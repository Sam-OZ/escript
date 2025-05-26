import os, time, datetime,requests

from dotenv import load_dotenv
from get_token import get_access_token


# ─── Load environment ───────────────────────────────────────────────────────────
load_dotenv()

# ─── Configuration ───────────────────────────────────────────────────────────────
PBS_API_KEY       = os.getenv("PBS_API_KEY") or os.getenv("OCP_APIM_SUBSCRIPTION_KEY")
PBS_BASE_URL      = "https://data-api.health.gov.au/pbs/api/v3"

# ─── Fees & Caps ─────────────────────────────────────────────────────────────────
GENERAL_CAP       = 31.60
CONCESSIONAL_CAP  = 7.70
SCHED8_LOADING    = 4.94   # Dangerous drug loading
EXTRA_DISP_FEE    = 3.40   # Extra dispensing fee for non-S8
PFDI              = 1.33   # Pharmaceutical fee
DISPENSING_FEE    = 7.82   # Retail PBS dispensing fee (RP)
CONTAINER_FEE     = 1.26   # Container fee

# ─── Price Tuning Constants ──────────────────────────────────────────────────────
ADJUSTED_MARKUP   = 4.20   # Additional tuning added to DPMQ for WSD only
FDP_ADJUSTMENT    = 5.00   # Additional flat markup added to final dispense price for WSD only

# ─── Helper Functions ────────────────────────────────────────────────────────────
def markup_tier(amount):
    if amount <= 30.00:
        return 0.15 * amount
    if amount <= 45.00:
        return 4.50
    if amount <= 450.00:
        return 0.10 * amount
    if amount <= 1000.00:
        return 45.00
    if amount <= 2000.00:
        return 0.045 * amount
    return 90.00


def cap(price, limit):
    return round(min(price, limit), 2)

# ─── DPMQ Calculators ────────────────────────────────────────────────────────────
def DPMQ_calculate_PBS(base_price, quantity, is_schedule_8, container_fee, pfdi):
    price_to_pharmacist = base_price * quantity
    markup_val = markup_tier(price_to_pharmacist)
    disp_fee = DISPENSING_FEE if not is_schedule_8 else 11.00
    dpmq = price_to_pharmacist + markup_val + disp_fee + container_fee + pfdi
    return round(dpmq, 2)


# ─── PBS API Routines ───────────────────────────────────────────────────────────
def get_schedule(months_back=0):
    today = datetime.datetime.now()
    ref = (today.replace(day=1) - datetime.timedelta(days=1)) if months_back else today
    mon, yr = ref.strftime('%B').upper(), ref.year
    backoff = 1
    for attempt in range(3):
        r = requests.get(f"{PBS_BASE_URL}/schedules?limit=100", headers={'subscription-key': PBS_API_KEY})
        try:
            r.raise_for_status()
            for s in r.json().get('data', []):
                if s.get('effective_month','').upper() == mon and s.get('effective_year') == yr:
                    return s['schedule_code']
            raise Exception(f"No schedule for {mon} {yr}")
        except requests.exceptions.HTTPError:
            if r.status_code == 429 and attempt < 2:
                time.sleep(backoff); backoff *= 2; continue
            raise
    raise Exception('Failed to fetch schedule')


def fetch_item(pbs_code, sched_code):
    backoff = 1
    for attempt in range(3):
        r = requests.get(f"{PBS_BASE_URL}/items", headers={'subscription-key': PBS_API_KEY}, params={'pbs_code': pbs_code, 'schedule_code': sched_code, 'limit':1})
        try:
            r.raise_for_status()
            data = r.json().get('data', [])
            if not data: raise Exception('PBS item not found')
            itm = data[0]; itm['schedule_code'] = sched_code; return itm
        except requests.exceptions.HTTPError:
            if r.status_code == 429 and attempt < 2:
                time.sleep(backoff); backoff*=2; continue
            raise
    raise Exception('Failed to fetch PBS item')


def fetch_rules(li_item_id: str) -> tuple[float|None, float]:
    """
    Pull the 'cmnwlth_dsp_price_max_qty' and brand_premium from the
    item-dispensing-rule-relationships endpoint. Only records with
    dispensing_rule_mnem of 'S90-CP' are used for DPMQ.
    """
    r = requests.get(
        f"{PBS_BASE_URL}/item-dispensing-rule-relationships",
        headers={"subscription-key": PBS_API_KEY},
        params={"li_item_id": li_item_id, "limit": 50},
        timeout=10,
    )
    if r.status_code == 401:
        raise RuntimeError(
            f"Unauthorized: invalid PBS_API_KEY for /liitems/{li_item_id}/item-dispensing-rule-relationships"
        )
    r.raise_for_status()
    data = r.json().get("data", [])
    dpmq = None
    brand_premium = 0.0
    for rec in data:
        # Commonwealth dispensing price only from S90-CP mnemonic
        if rec.get("dispensing_rule_mnem", "").lower() == "s90-cp":
            val = rec.get("cmnwlth_dsp_price_max_qty")
            if val is not None:
                try:
                    dpmq = float(val)
                except ValueError:
                    pass
        # Brand premium if present
        bp = rec.get("brand_premium")
        if bp is not None:
            try:
                brand_premium = float(bp)
            except ValueError:
                pass
    return (dpmq, brand_premium)

# ─── Pricing Functions ──────────────────────────────────────────────────────────
# def price_pbs():
    pbs_code = input("Enter PBS code: ").strip().upper()
    sched_num = input("Schedule number (8 or blank): ").strip()
    qty = int(input("Enter N_pack: ") or 1)
    auth = input("Authority & Medicare? (y/n): ").strip().lower() == 'y'
    conc = input("Concession eligible? (y/n): ").strip().lower() == 'y'
    is_s8 = (sched_num == '8')

    sched0 = get_schedule(0); sched1 = get_schedule(1)
    try:item = fetch_item(pbs_code, sched0)
    except:item = fetch_item(pbs_code, sched1)
    base_price=float(item['determined_price'])
    dpmq_val, brand_pr = fetch_rules(item['li_item_id'], sched0, sched1)
    D = dpmq_val if dpmq_val is not None else base_price*qty
    if dpmq_val is not None:
        fdp_raw = D + (SCHED8_LOADING if is_s8 else EXTRA_DISP_FEE + PFDI)
    else:
        fdp_raw = D + markup_tier(D) + (SCHED8_LOADING if is_s8 else DISPENSING_FEE + CONTAINER_FEE + EXTRA_DISP_FEE + PFDI)
    FDP = round(fdp_raw,2)
    general_cost = cap(FDP, GENERAL_CAP) if auth else FDP
    concess_cost = cap(FDP, CONCESSIONAL_CAP) if auth and conc else 0.0
    brand_cost = round((general_cost if auth else FDP)+brand_pr,2)
    print({'DPMQ':D,'FDP':FDP,'General':general_cost,'Concessional':concess_cost,'Brand':brand_cost})
#--- Price Calcu -------------------------
def calc_pbs_price(
    pbs_code: str,
    schedule_code: str|None = None,
    quantity: int = 1,
    authority_medicare: bool = False,
    concession_eligible: bool = False,
) -> dict:
    code = pbs_code.strip().upper()
    sched = schedule_code or get_schedule(0)
    item  = fetch_item(code, sched)

    base_price = float(item["determined_price"])
    dpmq_val, brand_pr = fetch_rules(item["li_item_id"])
    D = dpmq_val if dpmq_val is not None else base_price * quantity

    if sched == "8":
        fdp_raw = D + EXTRA_DISP_FEE + PFDI  # schedule-8 flat load
    elif dpmq_val is not None:
        fdp_raw = D + EXTRA_DISP_FEE + PFDI
    else:
        fdp_raw = D + markup_tier(D) + (
            DISPENSING_FEE + CONTAINER_FEE + EXTRA_DISP_FEE + PFDI
        )

    FDP = round(fdp_raw, 2)
    general_cost = cap(FDP, GENERAL_CAP) if authority_medicare else FDP
    concess_cost = (
        cap(FDP, CONCESSIONAL_CAP)
        if (authority_medicare and concession_eligible) else 0.0
    )
    brand_cost = round((general_cost if authority_medicare else FDP) + brand_pr, 2)

    return {
        "schedule":      sched,
        "DPMQ":          D,
        "FDP":           FDP,
        "General":       general_cost,
        "Concessional":  concess_cost,
        "Brand":         brand_cost,
    }
