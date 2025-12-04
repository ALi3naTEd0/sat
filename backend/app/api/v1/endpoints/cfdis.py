"""
CFDI Endpoints - API routes for managing CFDIs
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from typing import List, Optional
from datetime import datetime, date
import os
import uuid as uuid_lib

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models import User, CFDI, TipoComprobante, CFDIStatus
from app.services.cfdi_parser import CFDIParser
from decimal import Decimal

router = APIRouter(prefix="/cfdis", tags=["cfdis"])


# Pydantic schemas
from pydantic import BaseModel, Field

class CFDIUploadResponse(BaseModel):
    id: int
    uuid: str
    message: str

class CFDIListResponse(BaseModel):
    total: int
    cfdis: List[dict]

class CFDIStatsResponse(BaseModel):
    total_cfdis: int
    total_ingresos: float
    total_egresos: float
    total_nominas: int
    deducibles: int


@router.post("/upload", response_model=CFDIUploadResponse)
async def upload_cfdi(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and parse a CFDI XML file
    """
    if not file.filename.endswith('.xml'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos XML"
        )
    
    try:
        # Read XML content
        content = await file.read()
        xml_content = content.decode('utf-8')
        
        # Parse CFDI
        parser = CFDIParser(xml_content=xml_content)
        cfdi_data = parser.parse()
        
        # Check if UUID already exists
        existing = db.query(CFDI).filter(
            CFDI.uuid == cfdi_data['uuid'],
            CFDI.user_id == current_user.id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"CFDI con UUID {cfdi_data['uuid']} ya existe"
            )
        
        # Save XML file
        upload_dir = f"uploads/cfdis/{current_user.id}"
        os.makedirs(upload_dir, exist_ok=True)
        xml_filename = f"{cfdi_data['uuid']}.xml"
        xml_path = os.path.join(upload_dir, xml_filename)
        
        with open(xml_path, 'wb') as f:
            f.write(content)
        
        # Extract tax details
        impuestos = cfdi_data.get('impuestos', {})
        iva = 0
        isr = 0
        
        for traslado in impuestos.get('traslados', []):
            if traslado.get('impuesto') == '002':  # IVA
                iva += float(traslado.get('importe', 0))
        
        for retencion in impuestos.get('retenciones', []):
            if retencion.get('impuesto') == '001':  # ISR
                isr += float(retencion.get('importe', 0))
        
        # Create CFDI record
        cfdi = CFDI(
            user_id=current_user.id,
            uuid=cfdi_data['uuid'],
            serie=cfdi_data.get('serie'),
            folio=cfdi_data.get('folio'),
            version=cfdi_data.get('version'),
            tipo_comprobante=TipoComprobante(cfdi_data['tipo_comprobante']),
            fecha_emision=cfdi_data['fecha'],
            fecha_timbrado=cfdi_data.get('timbre', {}).get('fecha_timbrado'),
            emisor_rfc=cfdi_data['emisor']['rfc'],
            emisor_nombre=cfdi_data['emisor']['nombre'],
            emisor_regimen_fiscal=cfdi_data['emisor'].get('regimen_fiscal'),
            receptor_rfc=cfdi_data['receptor']['rfc'],
            receptor_nombre=cfdi_data['receptor']['nombre'],
            receptor_uso_cfdi=cfdi_data['receptor'].get('uso_cfdi'),
            receptor_domicilio_fiscal=cfdi_data['receptor'].get('domicilio_fiscal'),
            receptor_regimen_fiscal=cfdi_data['receptor'].get('regimen_fiscal'),
            moneda=cfdi_data.get('moneda', 'MXN'),
            tipo_cambio=cfdi_data.get('tipo_cambio', Decimal('1.0')),
            subtotal=cfdi_data['subtotal'],
            descuento=cfdi_data.get('descuento', Decimal('0')),
            total=cfdi_data['total'],
            total_impuestos_trasladados=impuestos.get('total_impuestos_trasladados', Decimal('0')),
            total_impuestos_retenidos=impuestos.get('total_impuestos_retenidos', Decimal('0')),
            iva_trasladado=Decimal(str(iva)),
            isr_retenido=Decimal(str(isr)),
            metodo_pago=cfdi_data.get('metodo_pago'),
            forma_pago=cfdi_data.get('forma_pago'),
            es_ingreso=parser.is_ingreso(),
            es_egreso=parser.is_egreso(),
            es_nomina=parser.is_nomina(),
            es_deducible=parser.is_deducible(),
            status=CFDIStatus.VIGENTE,
            conceptos=cfdi_data.get('conceptos'),
            impuestos_detalle=impuestos,
            timbre_data=cfdi_data.get('timbre'),
            xml_path=xml_path
        )
        
        db.add(cfdi)
        db.commit()
        db.refresh(cfdi)
        
        return CFDIUploadResponse(
            id=cfdi.id,
            uuid=cfdi.uuid,
            message="CFDI cargado exitosamente"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar CFDI: {str(e)}"
        )


@router.get("/", response_model=CFDIListResponse)
def list_cfdis(
    year: Optional[int] = Query(None, description="Filtrar por año"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filtrar por mes"),
    tipo: Optional[str] = Query(None, description="Tipo de comprobante (I, E, N, P)"),
    deducible: Optional[bool] = Query(None, description="Solo deducibles"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List user's CFDIs with filters
    """
    query = db.query(CFDI).filter(CFDI.user_id == current_user.id)
    
    # Apply filters
    if year:
        query = query.filter(extract('year', CFDI.fecha_emision) == year)
    
    if month:
        query = query.filter(extract('month', CFDI.fecha_emision) == month)
    
    if tipo:
        query = query.filter(CFDI.tipo_comprobante == tipo)
    
    if deducible is not None:
        query = query.filter(CFDI.es_deducible == deducible)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    cfdis = query.order_by(CFDI.fecha_emision.desc()).offset(offset).limit(limit).all()
    
    return CFDIListResponse(
        total=total,
        cfdis=[cfdi.to_dict() for cfdi in cfdis]
    )


@router.get("/stats", response_model=CFDIStatsResponse)
def get_cfdi_stats(
    year: Optional[int] = Query(None, description="Filtrar por año"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get CFDI statistics for user
    """
    query = db.query(CFDI).filter(CFDI.user_id == current_user.id)
    
    if year:
        query = query.filter(extract('year', CFDI.fecha_emision) == year)
    
    # Count totals
    total_cfdis = query.count()
    
    # Sum ingresos
    ingresos = query.filter(CFDI.es_ingreso == True).with_entities(
        func.sum(CFDI.total)
    ).scalar() or 0
    
    # Sum egresos
    egresos = query.filter(CFDI.es_egreso == True).with_entities(
        func.sum(CFDI.total)
    ).scalar() or 0
    
    # Count nominas
    nominas = query.filter(CFDI.es_nomina == True).count()
    
    # Count deducibles
    deducibles = query.filter(CFDI.es_deducible == True).count()
    
    return CFDIStatsResponse(
        total_cfdis=total_cfdis,
        total_ingresos=float(ingresos),
        total_egresos=float(egresos),
        total_nominas=nominas,
        deducibles=deducibles
    )


@router.get("/{cfdi_id}")
def get_cfdi_detail(
    cfdi_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed CFDI information
    """
    cfdi = db.query(CFDI).filter(
        CFDI.id == cfdi_id,
        CFDI.user_id == current_user.id
    ).first()
    
    if not cfdi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CFDI no encontrado"
        )
    
    return cfdi.to_dict()


@router.delete("/{cfdi_id}")
def delete_cfdi(
    cfdi_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a CFDI
    """
    cfdi = db.query(CFDI).filter(
        CFDI.id == cfdi_id,
        CFDI.user_id == current_user.id
    ).first()
    
    if not cfdi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CFDI no encontrado"
        )
    
    # Delete XML file if exists
    if cfdi.xml_path and os.path.exists(cfdi.xml_path):
        os.remove(cfdi.xml_path)
    
    db.delete(cfdi)
    db.commit()
    
    return {"message": "CFDI eliminado exitosamente"}
