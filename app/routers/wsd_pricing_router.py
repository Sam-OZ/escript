# app/routers/wsd_pricing_router.py

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response
import json

from app.services.wsd_pricing import WsdPriceService

router = APIRouter(prefix="/pricing/wsd", tags=["wsd_pricing"])
_service = WsdPriceService()

@router.get("/{gtin}")
def wsd_price(
    gtin: str,
    qty: int  = Query(1,     description="Quantity"),
    auth: bool = Query(False, description="Authority Medicare?"),
    conc: bool = Query(False, description="Concession eligible?"),
):
    try:
        result = _service.calc_price(
            gtin=gtin,
            quantity=qty,
            authority_medicare=auth,
            concession_eligible=conc,
        )
        return Response(content=json.dumps(result, indent=2), media_type="application/json")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
