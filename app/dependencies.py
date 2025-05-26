# app/dependencies.py
from fastapi import Depends
from app.services.token_service import token_service
from app.services.prescription_service import PrescriptionService

def get_token_service():
    return token_service

def get_prescription_service(
    token_svc = Depends(get_token_service)
) -> PrescriptionService:
    return PrescriptionService(token_svc)
