# app/services/wsd_pricing.py

import csv
from pathlib import Path
from fastapi import HTTPException

from app.services.pbs_pricing import (
    markup_tier, cap,
    DISPENSING_FEE, CONTAINER_FEE, EXTRA_DISP_FEE, PFDI,
    GENERAL_CAP, CONCESSIONAL_CAP,
)

# Additional tuning constants for WSD
ADJUSTED_MARKUP = 4.20   # Additional tuning added to DPMQ for WSD only
FDP_ADJUSTMENT  = 5.00   # Additional flat markup added to final dispense price for WSD only

# Path to your CSV database (at project root)
CSV_PATH = Path(__file__).parent.parent / "Pricebook_1055053.csv"

class WsdPriceService:
    def __init__(self, csv_path: Path = CSV_PATH):
        self.csv_path = csv_path

    def calc_price(
        self,
        gtin: str,
        quantity: int = 1,
        authority_medicare: bool = False,
        concession_eligible: bool = False,
    ) -> dict:
                # 1. Lookup base price in CSV: GTIN in column 4, price in column 9
        try:
            with open(self.csv_path, newline="") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                if len(headers) < 9:
                    raise HTTPException(500, f"Expected at least 9 columns in CSV, found {len(headers)}")
                gtin_col = headers[3]   # 4th column
                base_col = headers[8]   # 9th column
                base_price = None
                for row in reader:
                    if row.get(gtin_col) == gtin:
                        try:
                            base_price = float(row.get(base_col, 0))
                        except ValueError:
                            raise HTTPException(500, f"Invalid base price value '{row.get(base_col)}' for GTIN {gtin}")
                        break
                if base_price is None:
                    raise HTTPException(404, f"No WSD entry for GTIN {gtin}")
        except FileNotFoundError:
            raise HTTPException(500, f"Pricebook file not found at {self.csv_path}")

        # 2. Compute DPMQ using tier markup Compute DPMQ using tier markup
        D = base_price * quantity

        # 3. Final Dispense Price (FDP)
        fdp_raw = (
            D
            + markup_tier(D)
            + DISPENSING_FEE
            + CONTAINER_FEE
            + EXTRA_DISP_FEE
            + PFDI
            + FDP_ADJUSTMENT
        )
        FDP = round(fdp_raw, 2)

        # 4. Caps
        general_cost     = cap(FDP, GENERAL_CAP) if authority_medicare else FDP
        concessional_cost = cap(FDP, CONCESSIONAL_CAP) if (authority_medicare and concession_eligible) else 0.0

        # 5. Brand (WSD-specific tuning)
        brand_cost = round(D + ADJUSTED_MARKUP, 2)

        return {
            "GTIN":           gtin,
            "quantity":       quantity,
            "BasePrice":      base_price,
            "DPMQ":           D,
            "FDP":            FDP,
            "General":        general_cost,
            "Concessional":   concessional_cost,
            "Brand":          brand_cost,
        }
