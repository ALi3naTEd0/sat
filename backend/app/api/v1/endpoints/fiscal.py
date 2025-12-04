"""
API Router - Fiscal Profile Management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.fiscal_profile import FiscalProfile
from app.schemas.fiscal_profile import (
    FiscalProfileCreate,
    FiscalProfileUpdate,
    FiscalProfileResponse,
    RFCValidation,
    CURPLookup
)
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter(prefix="/fiscal", tags=["Fiscal Profile"])


@router.get("/profile", response_model=FiscalProfileResponse)
async def get_fiscal_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's fiscal profile"""
    
    fiscal_profile = db.query(FiscalProfile).filter(
        FiscalProfile.user_id == current_user.id
    ).first()
    
    if not fiscal_profile:
        # Create empty profile automatically
        fiscal_profile = FiscalProfile(
            user_id=current_user.id,
            curp=current_user.curp
        )
        db.add(fiscal_profile)
        db.commit()
        db.refresh(fiscal_profile)
    
    return fiscal_profile


@router.post("/profile", response_model=FiscalProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_fiscal_profile(
    profile_data: FiscalProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create fiscal profile for user"""
    
    # Check if profile already exists
    existing_profile = db.query(FiscalProfile).filter(
        FiscalProfile.user_id == current_user.id
    ).first()
    
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal profile already exists"
        )
    
    # Check if RFC already exists
    if profile_data.rfc:
        existing_rfc = db.query(FiscalProfile).filter(
            FiscalProfile.rfc == profile_data.rfc
        ).first()
        if existing_rfc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RFC already registered"
            )
    
    # Create fiscal profile
    fiscal_profile = FiscalProfile(
        user_id=current_user.id,
        rfc=profile_data.rfc,
        curp=profile_data.curp or current_user.curp,
        legal_name=profile_data.legal_name,
        tax_regime=profile_data.tax_regime,
        fiscal_address=profile_data.fiscal_address or {}
    )
    
    db.add(fiscal_profile)
    db.commit()
    db.refresh(fiscal_profile)
    
    return fiscal_profile


@router.put("/profile", response_model=FiscalProfileResponse)
async def update_fiscal_profile(
    profile_update: FiscalProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update fiscal profile"""
    
    fiscal_profile = db.query(FiscalProfile).filter(
        FiscalProfile.user_id == current_user.id
    ).first()
    
    if not fiscal_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fiscal profile not found"
        )
    
    # Check if RFC is being changed and if it's already in use
    if profile_update.rfc is not None and profile_update.rfc != fiscal_profile.rfc:
        existing_rfc = db.query(FiscalProfile).filter(
            FiscalProfile.rfc == profile_update.rfc,
            FiscalProfile.id != fiscal_profile.id
        ).first()
        if existing_rfc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RFC already registered by another user"
            )
        fiscal_profile.rfc = profile_update.rfc
    
    # Update fields
    if profile_update.curp is not None:
        fiscal_profile.curp = profile_update.curp
    if profile_update.legal_name is not None:
        fiscal_profile.legal_name = profile_update.legal_name
    if profile_update.tax_regime is not None:
        fiscal_profile.tax_regime = profile_update.tax_regime
    if profile_update.fiscal_address is not None:
        fiscal_profile.fiscal_address = profile_update.fiscal_address
    if profile_update.tax_mailbox_email is not None:
        fiscal_profile.tax_mailbox_email = profile_update.tax_mailbox_email
    
    db.commit()
    db.refresh(fiscal_profile)
    
    return fiscal_profile


@router.post("/validate-rfc")
async def validate_rfc(
    rfc_data: RFCValidation,
    current_user: User = Depends(get_current_user)
):
    """Validate RFC format and check with SAT"""
    
    # TODO: Implement RFC validation logic
    # - Format validation
    # - Check digit validation
    # - SAT API validation (if available)
    
    return {
        "valid": True,
        "rfc": rfc_data.rfc,
        "message": "RFC validation not fully implemented yet"
    }


@router.post("/lookup-curp")
async def lookup_curp(
    curp_data: CURPLookup,
    current_user: User = Depends(get_current_user)
):
    """Lookup RFC by CURP"""
    
    # Validate CURP format
    curp = curp_data.curp.upper()
    if len(curp) != 18:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CURP debe tener 18 caracteres"
        )
    
    # Extract RFC from CURP (first 10 characters for persons, or 12 for legal entities)
    # For natural persons, RFC = first 10 chars of CURP + homoclave (2 chars)
    # Since we don't have the homoclave, we return the base RFC
    rfc_base = curp[:10]
    
    return {
        "success": True,
        "curp": curp,
        "rfc": rfc_base,
        "message": "RFC base obtenido del CURP. Necesitarás agregar la homoclave (2 dígitos finales).",
        "note": "El RFC completo consta de: " + rfc_base + "XX (donde XX es tu homoclave)"
    }
    # - Retrieve RFC if exists
    
    return {
        "curp": curp_data.curp,
        "rfc": None,
        "message": "CURP lookup not fully implemented yet"
    }


# Prestaciones endpoints
from app.services.prestaciones_calculator import PrestacionesCalculator
from pydantic import BaseModel
from typing import Optional


class PrestacionesResponse(BaseModel):
    year: int
    ingresos: dict
    deducciones: dict
    impuestos: dict
    base_gravable: float
    total_cfdis: int
    ultimo_calculo: Optional[str]


@router.get("/prestaciones/{year}", response_model=PrestacionesResponse)
async def get_prestaciones(
    year: int,
    recalcular: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get prestaciones (income and deductions) for a specific year
    """
    from app.models import PrestacionAnual
    
    # Get or calculate prestaciones
    prestacion = db.query(PrestacionAnual).filter(
        PrestacionAnual.user_id == current_user.id,
        PrestacionAnual.year == year
    ).first()
    
    if not prestacion or recalcular:
        # Calculate/recalculate
        calculator = PrestacionesCalculator(db)
        prestacion = calculator.calculate_year(current_user.id, year)
    
    return PrestacionesResponse(
        year=prestacion.year,
        ingresos={
            'total': float(prestacion.total_ingresos),
            'sueldos': float(prestacion.ingresos_sueldos),
            'actividad_empresarial': float(prestacion.ingresos_actividad_empresarial),
            'arrendamiento': float(prestacion.ingresos_arrendamiento),
            'intereses': float(prestacion.ingresos_intereses),
            'otros': float(prestacion.otros_ingresos)
        },
        deducciones={
            'total': float(prestacion.total_deducciones),
            'gastos_medicos': float(prestacion.gastos_medicos),
            'intereses_hipotecarios': float(prestacion.intereses_hipotecarios),
            'educacion': float(prestacion.educacion),
            'seguros': float(prestacion.seguros),
            'transporte_escolar': float(prestacion.transporte_escolar),
            'donativos': float(prestacion.donativos),
            'otras': float(prestacion.otras_deducciones)
        },
        impuestos={
            'isr_retenido': float(prestacion.isr_retenido),
            'isr_pagado': float(prestacion.isr_pagado),
            'iva_pagado': float(prestacion.iva_pagado)
        },
        base_gravable=float(prestacion.base_gravable),
        total_cfdis=prestacion.total_cfdis,
        ultimo_calculo=prestacion.ultimo_calculo.isoformat() if prestacion.ultimo_calculo else None
    )


@router.get("/prestaciones/{year}/monthly")
async def get_monthly_breakdown(
    year: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get monthly income breakdown for a year
    """
    calculator = PrestacionesCalculator(db)
    monthly_data = calculator.get_monthly_breakdown(current_user.id, year)
    
    return {
        'year': year,
        'monthly': monthly_data
    }


@router.get("/deducciones/{year}")
async def get_deducciones_detalle(
    year: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed deductions breakdown by category
    """
    calculator = PrestacionesCalculator(db)
    breakdown = calculator.get_deduction_breakdown(current_user.id, year)
    
    # Calculate totals
    totals = {
        category: sum(cfdi['total'] for cfdi in cfdis)
        for category, cfdis in breakdown.items()
    }
    
    return {
        'year': year,
        'breakdown': breakdown,
        'totals': totals,
        'total_general': sum(totals.values())
    }
