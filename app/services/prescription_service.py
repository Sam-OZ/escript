# app/services/prescription_service.py
import logging
import requests
import re
from app.settings import settings

log = logging.getLogger("prescription_service")

class PrescriptionService:
    def __init__(self, token_service):
        self.token_svc = token_service

    def fetch_raw_bundle(self, scid: str) -> dict:
        token = self.token_svc.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Ocp-Apim-Subscription-Key": settings.ocp_apim_subscription_key
        }
        params = {
            "identifier": f"http://fhir.erx.com.au/NamingSystem/identifiers#scid|{scid}",
            "_format": "json"
        }
        resp = requests.get(
            f"{settings.fhir_api_base}/MedicationRequest",
            headers=headers,
            params=params,
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()

    def extract_allergies(self, bundle: dict) -> list[str]:
        # Placeholder for allergy extraction
        return []

    def extract_notes(self, med_request: dict) -> str:
        notes = med_request.get("note", [])
        return "; ".join(n.get("text", "") for n in notes)

    def extract_coding(self, code_block: dict, system: str) -> str:
        for c in code_block.get("coding", []):
            if c.get("system") == system:
                return c.get("code")
        return "N/A"

    def summarize(self, scid: str) -> dict:
        log.info("Summarizing SCID %s", scid)
        bundle = self.fetch_raw_bundle(scid)
        entries = bundle.get("entry", [])
        if not entries:
            raise ValueError(f"No data for SCID {scid}")

        mr = entries[0]["resource"]
        # Find Patient resource in contained
        patient = next((c for c in mr.get("contained", []) if c.get("resourceType") == "Patient"), {})
        # Build PID map
        pid_map = {sid.get("system"): sid.get("value") for sid in patient.get("identifier", [])}

        # Patient demographics
        full_name = patient.get("name", [{}])[0].get("text") or \
                    " ".join(patient.get("name", [{}])[0].get("given", []) + [patient.get("name", [{}])[0].get("family", "")])
        dob = patient.get("birthDate", "N/A")

        # Find Medication resource
        med = next((c for c in mr.get("contained", []) if c.get("resourceType") == "Medication"), {})
        # Dispense info
        dispense = mr.get("dispenseRequest", {})

        # Extract core fields
        med_no = pid_map.get("http://ns.electronichealth.net.au/id/medicare-number", "N/A")
        irn = pid_map.get("http://fhir.erx.com.au/NamingSystem/identifiers#authority-script-number", "N/A")
        pension = pid_map.get("http://ns.electronichealth.net.au/id/pensioner-concession-card", "N/A")
        seniors = pid_map.get("http://ns.electronichealth.net.au/id/commonwealth-seniors-health-card", "N/A")
        reps_allowed = dispense.get("numberOfRepeatsAllowed")
        disp_count = dispense.get("repeatsDispensed")
        reps_remain = reps_allowed - disp_count if reps_allowed is not None and disp_count is not None else None
        prescribed_qty = dispense.get("quantity", {}).get("value")
        max_qty_auth = dispense.get("quantity", {}).get("value")
        package_qty = dispense.get("expectedSupplyDuration", {}).get("value")

        # Medication details
        med_ext = {ext.get("url").split("/")[-1]: ext.get("valueString") or ext.get("valueBoolean")
                   for ext in mr.get("extension", [])}
        med_strength = med.get("extension", [{}])[0].get("valueString")
        med_form = med.get("form", {}).get("text")

        return {
            "medicare_no": med_no,
            "irn": irn,
            "ihi": pid_map.get("http://ns.electronichealth.net.au/id/hi/ihi/1.0", "N/A"),
            "racf": pid_map.get("http://ns.electronichealth.net.au/id/racf-id", "N/A"),
            "pension_card": pension,
            "seniors_card": seniors,
            "pensioner_elig": False,
            "seniors_elig": False,
            "name": full_name,
            "dob": dob,
            "allergies": self.extract_allergies(bundle),
            "prescriber_notes": self.extract_notes(mr),
            "aip_drug_name": med_ext.get("aip-complient-drug-name", "N/A"),
            "brand_name": med_ext.get("medication-brand-name", "N/A"),
            "generic_name": med_ext.get("medication-generic-name", "N/A"),
            "item_generic_intension": med_ext.get("item-generic-intension", "N/A"),
            "schedule_number": med_ext.get("schedule-number", "N/A"),
            "private_prescription": str(med_ext.get("private-prescription", "N/A")),
            "repeats_allowed": reps_allowed,
            "repeats_dispensed": disp_count,
            "repeats_remaining": reps_remain,
            "snomed": self.extract_coding(med.get("code", {}), "http://snomed.info/sct"),
            "gtin": self.extract_coding(med.get("code", {}), "http://www.gs1.org/gtin"),
            "med_text": med.get("code", {}).get("text", "N/A"),
            "pbs_code": next(
                (c.get("code") for c in med.get("code", {}).get("coding", [])
                 if re.match(r"^[0-9]{1,5}[A-Z]$", c.get("code", ""))),
                "N/A"
            ),
            "prescribed_qty": prescribed_qty,
            "max_qty_auth": max_qty_auth,
            "package_qty": package_qty,
            "med_strength": med_strength,
            "med_form": med_form
        }
