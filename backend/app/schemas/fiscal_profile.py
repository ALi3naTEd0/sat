"""
Pydantic Schemas - Fiscal Profile
"""
from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# Fiscal Profile Create/Update
class FiscalProfileCreate(BaseModel):
    rfc: Optional[str] = Field(None, min_length=12, max_length=13)
    curp: Optional[str] = Field(None, min_length=18, max_length=18)
    legal_name: Optional[str] = None
    tax_regime: Optional[str] = None
    fiscal_address: Optional[Dict] = None


class FiscalProfileUpdate(BaseModel):
    rfc: Optional[str] = Field(None, min_length=12, max_length=13)
    curp: Optional[str] = Field(None, min_length=18, max_length=18)
    legal_name: Optional[str] = None
    tax_regime: Optional[str] = None
    fiscal_address: Optional[Dict] = None
    tax_mailbox_email: Optional[str] = None


# Fiscal Profile Response
class FiscalProfileResponse(BaseModel):
    id: int
    user_id: int
    rfc: Optional[str]
    curp: Optional[str]
    legal_name: Optional[str]
    tax_regime: Optional[str]
    fiscal_status: str
    fiscal_address: Optional[Dict]
    obligations: List[str]
    tax_mailbox_active: bool
    has_efirma: bool
    efirma_expiry: Optional[datetime]
    has_sat_password: bool
    compliance_opinion: Optional[Dict]
    last_compliance_check: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# RFC Validation Request
class RFCValidation(BaseModel):
    rfc: str = Field(..., min_length=12, max_length=13)


# CURP Lookup Request
class CURPLookup(BaseModel):
    curp: str = Field(..., min_length=18, max_length=18)


# Compliance Opinion Response
class ComplianceOpinion(BaseModel):
    status: str  # "positive", "negative", "unknown"
    date: Optional[datetime]
    valid_until: Optional[datetime]
    details: Optional[Dict]
