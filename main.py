from dotenv import load_dotenv
load_dotenv()    # must be first, so services pick up os.environ

from fastapi import FastAPI
from app.routers.prescription          import router as prescription_router
from app.routers.pbs_pricing_router   import router as pbs_pricing_router
from app.routers.wsd_pricing_router   import router as wsd_pricing_router

app = FastAPI(title="Medication + Pricing API")

app.include_router(prescription_router)
app.include_router(pbs_pricing_router)
app.include_router(wsd_pricing_router)

# (any debug or health-check endpoints you have)


@app.get("/_debug/token")
def debug_token():
    tok = token_service.get_token()
    return {"token_sample": tok[:30] + "...", "type": type(tok).__name__}

@app.get("/_debug/bundle/{scid}")
def debug_bundle(scid: str):
    """
    Returns raw HTTP response (status, headers, body) for the FHIR bundle request.
    """
    token = token_service.get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Ocp-Apim-Subscription-Key": settings.ocp_apim_subscription_key
    }
    params = {"identifier": f"http://fhir.erx.com.au/NamingSystem/identifiers#scid|{scid}"}
    resp = requests.get(
        f"{settings.fhir_api_base}/MedicationRequest",
        headers=headers,
        params=params,
        timeout=10
    )
    return {
        "status_code": resp.status_code,
        "headers": dict(resp.headers),
        "body": resp.text
    }

@app.get("/health")
def healthcheck():
    return {"status": "ok"}
