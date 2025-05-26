# app/routers/prescription.py
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import JSONResponse, Response
import json
from typing import List
from app.services.prescription_service import PrescriptionService
from app.services.token_service import token_service

router = APIRouter(prefix="/prescription", tags=["prescription"])

def get_prescription_service():
    return PrescriptionService(token_service)

@router.get("/{scid}")
def fetch_scid(scid: str, svc: PrescriptionService = Depends(get_prescription_service)):
    try:
        data = svc.summarize(scid)
        return Response(content=json.dumps(data, indent=2), media_type="application/json")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.post("/batch")
def fetch_batch(
    scids: List[str] = Body(..., example=["21KR32KDBCY38MCDW7", "anotherSCID"]),
    svc: PrescriptionService = Depends(get_prescription_service)
):
    """
    Accepts a JSON array of SCIDs, returns a list of summaries.
    Usage with curl:
      curl -X POST http://127.0.0.1:8000/prescription/batch \
           -H 'Content-Type: application/json' \
           -d '["21KR32KDBCY38MCDW7", "anotherSCID"]'
    """
    results = []
    for s in scids:
        try:
            results.append(svc.summarize(s))
        except Exception:
            continue
    return Response(content=json.dumps(results, indent=2), media_type="application/json")
