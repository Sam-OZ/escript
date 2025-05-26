from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
import json
from app.services.pbs_pricing import calc_pbs_price

router = APIRouter(prefix="/pricing/pbs", tags=["pbs_pricing"])

@router.get("/{pbs_code}")
def pbs_price(
    pbs_code: str,
    qty:     int    = Query(1,     description="Quantity"),
    auth:    bool   = Query(False, description="Authority Medicare?"),
    conc:    bool   = Query(False, description="Concession eligible?"),
    sched:   str|None = Query(None, description="Override schedule code"),
):
    try:
        result = calc_pbs_price(
            pbs_code=pbs_code,
            schedule_code=sched,
            quantity=qty,
            authority_medicare=auth,
            concession_eligible=conc,
        )
        return Response(content=json.dumps(result, indent=2), media_type="application/json")
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
