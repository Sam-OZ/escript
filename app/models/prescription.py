# app/models/prescription.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class MedicationSummary(BaseModel):
    id: str
    status: str
    intent: str
    authoredOn: str
    medication: Optional[str]
    identifiers: List[str]
    item_generic_intension: Optional[str]
    schedule_number: Optional[int]
    private_prescription: Optional[bool]
    ihi: Optional[str]

    model_config = ConfigDict(from_attributes=True)
