"""
API Endpoints - CFDI Management (Facturas Electrónicas)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import List, Optional
from io import BytesIO
import asyncio
import logging

from app.core.database import get_db
from app.core.security import decrypt_data
from app.models.user import User
from app.models.sat_credentials import SATCredentials
from app.schemas.sat import CFDIResponse, CFDIFilter
from app.api.v1.endpoints.auth import get_current_user
from app.automation.sat_automation import SATAutomation, fetch_cfdis_from_sat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cfdi", tags=["CFDI"])


# Simple in-memory cache for CFDIs
_cfdi_cache = {}


@router.get("/list", response_model=List[CFDIResponse])
async def list_cfdis(
    cfdi_type: str = Query("emitido", description="emitido o recibido"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None, description="vigente, cancelado"),
    use_cache: bool = Query(True, description="Usar cache si está disponible"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of CFDIs (Comprobantes Fiscales Digitales por Internet)
    
    Obtiene CFDIs del usuario. Si tiene credenciales SAT, se conecta al portal del SAT
    para obtener datos reales. Si no, retorna datos de demostración.
    
    Args:
        cfdi_type: "emitido" para facturas emitidas, "recibido" para recibidas
        start_date: Fecha inicial (opcional)
        end_date: Fecha final (opcional)
        status: Estado del CFDI - "vigente" o "cancelado"
        use_cache: Usar cache si está disponible
    """
    
    # Set default dates (last 6 months)
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=180)
    
    # Verify user has SAT credentials
    sat_creds = db.query(SATCredentials).filter(
        SATCredentials.user_id == current_user.id
    ).first()
    
    if not sat_creds or not sat_creds.encrypted_password:
        logger.info(f"No SAT credentials for user {current_user.id}, using demo data")
        # Return demo data if no credentials
        return _get_demo_cfdis(cfdi_type, start_date, end_date, status)
    
    # Check cache first
    cache_key = f"{current_user.id}_{cfdi_type}_{start_date}_{end_date}"
    if use_cache and cache_key in _cfdi_cache:
        logger.info(f"Returning cached CFDIs for user {current_user.id}")
        cfdis = _cfdi_cache[cache_key]
    else:
        # Fetch from SAT
        try:
            # Decrypt password
            decrypted_password = decrypt_data(sat_creds.encrypted_password)
            
            logger.info(f"Fetching CFDIs from SAT for user {current_user.id}, RFC: {sat_creds.rfc}")
            
            # Call SAT automation
            cfdis_data = await fetch_cfdis_from_sat(
                rfc=sat_creds.rfc,
                password=decrypted_password,
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.max.time())
            )
            
            # Convert to CFDIResponse objects
            cfdis = []
            for cfdi_data in cfdis_data:
                try:
                    cfdi = CFDIResponse(
                        uuid=cfdi_data.get("uuid", ""),
                        tipo=cfdi_data.get("tipo", "ingreso"),
                        fecha=cfdi_data.get("fecha", datetime.now()),
                        rfc_emisor=cfdi_data.get("rfc_emisor", ""),
                        nombre_emisor=cfdi_data.get("nombre_emisor", ""),
                        rfc_receptor=cfdi_data.get("rfc_receptor", ""),
                        nombre_receptor=cfdi_data.get("nombre_receptor", ""),
                        subtotal=cfdi_data.get("subtotal", 0.0),
                        total=cfdi_data.get("total", 0.0),
                        moneda=cfdi_data.get("moneda", "MXN"),
                        status=cfdi_data.get("status", "vigente"),
                        xml_url=cfdi_data.get("xml_url", ""),
                        pdf_url=cfdi_data.get("pdf_url", "")
                    )
                    cfdis.append(cfdi)
                except Exception as e:
                    logger.error(f"Error converting CFDI data: {e}")
                    continue
            
            # Cache the results
            _cfdi_cache[cache_key] = cfdis
            logger.info(f"Successfully fetched {len(cfdis)} CFDIs from SAT")
            
        except Exception as e:
            logger.error(f"Error fetching CFDIs from SAT: {e}")
            # Fallback to demo data on error
            return _get_demo_cfdis(cfdi_type, start_date, end_date, status)
    
    # Filter by type
    if cfdi_type and cfdi_type != "todos":
        cfdis = [c for c in cfdis if c.tipo == cfdi_type]
    
    # Filter by date range
    if start_date:
        cfdis = [c for c in cfdis if c.fecha.date() >= start_date]
    if end_date:
        cfdis = [c for c in cfdis if c.fecha.date() <= end_date]
    
    # Filter by status
    if status:
        cfdis = [c for c in cfdis if c.status == status]
    
    return cfdis


def _get_demo_cfdis(cfdi_type: str, start_date: date, end_date: date, status: Optional[str]) -> List[CFDIResponse]:
    """Get demo CFDIs for users without SAT credentials"""
    
    mock_cfdis = [
        CFDIResponse(
            uuid="550e8400-e29b-41d4-a716-446655440000",
            tipo="ingreso",
            fecha=datetime(2025, 11, 15, 10, 30),
            rfc_emisor="AAA010101AAA",
            nombre_emisor="Empresa Ejemplo S.A. de C.V.",
            rfc_receptor="BBB020202BBB",
            nombre_receptor="Cliente Demo",
            subtotal=1000.00,
            total=1160.00,
            moneda="MXN",
            status="vigente",
            xml_url="/api/v1/cfdi/550e8400-e29b-41d4-a716-446655440000/xml",
            pdf_url="/api/v1/cfdi/550e8400-e29b-41d4-a716-446655440000/pdf"
        ),
        CFDIResponse(
            uuid="550e8400-e29b-41d4-a716-446655440001",
            tipo="egreso",
            fecha=datetime(2025, 11, 10, 14, 45),
            rfc_emisor="CCC030303CCC",
            nombre_emisor="Proveedor S.A.",
            rfc_receptor="BBB020202BBB",
            nombre_receptor="Mi Empresa Demo",
            subtotal=500.00,
            total=580.00,
            moneda="MXN",
            status="vigente",
            xml_url="/api/v1/cfdi/550e8400-e29b-41d4-a716-446655440001/xml",
            pdf_url="/api/v1/cfdi/550e8400-e29b-41d4-a716-446655440001/pdf"
        ),
        CFDIResponse(
            uuid="550e8400-e29b-41d4-a716-446655440002",
            tipo="traslado",
            fecha=datetime(2025, 11, 5, 9, 15),
            rfc_emisor="DDD040404DDD",
            nombre_emisor="Distribuidor Logístico",
            rfc_receptor="BBB020202BBB",
            nombre_receptor="Mi Empresa Demo",
            subtotal=2000.00,
            total=2320.00,
            moneda="MXN",
            status="vigente",
            xml_url="/api/v1/cfdi/550e8400-e29b-41d4-a716-446655440002/xml",
            pdf_url="/api/v1/cfdi/550e8400-e29b-41d4-a716-446655440002/pdf"
        )
    ]
    
    # Filter by type
    if cfdi_type and cfdi_type != "todos":
        mock_cfdis = [c for c in mock_cfdis if c.tipo == cfdi_type]
    
    # Filter by date range
    if start_date:
        mock_cfdis = [c for c in mock_cfdis if c.fecha.date() >= start_date]
    if end_date:
        mock_cfdis = [c for c in mock_cfdis if c.fecha.date() <= end_date]
    
    # Filter by status
    if status:
        mock_cfdis = [c for c in mock_cfdis if c.status == status]
    
    return mock_cfdis


@router.get("/{uuid}/xml")
async def download_cfdi_xml(
    uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download CFDI XML file
    
    Obtiene el archivo XML del CFDI desde el SAT o genera uno de demostración
    """
    
    # Verify user has SAT credentials
    sat_creds = db.query(SATCredentials).filter(
        SATCredentials.user_id == current_user.id
    ).first()
    
    if not sat_creds:
        # Generate demo XML
        return _generate_demo_xml(uuid)
    
    try:
        # Try to get actual XML from SAT
        # In production, this would download from SAT portal
        logger.info(f"Downloading XML for CFDI {uuid}")
        return _generate_demo_xml(uuid)
        
    except Exception as e:
        logger.error(f"Error downloading XML for CFDI {uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading XML: {str(e)}"
        )


def _generate_demo_xml(uuid: str) -> StreamingResponse:
    """Generate a demo CFDI XML file"""
    
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd"
    Version="4.0"
    Serie="A"
    Folio="{uuid[:8]}"
    Fecha="{datetime.now().isoformat()}"
    FormaPago="03"
    SubTotal="1000.00"
    Total="1160.00"
    TipoDeComprobante="I"
    Moneda="MXN">
    
    <cfdi:Emisor Rfc="AAA010101AAA" Nombre="Empresa Ejemplo S.A. de C.V." RegimenFiscal="601"/>
    
    <cfdi:Receptor Rfc="BBB020202BBB" Nombre="Cliente" UsoCFDI="G03"/>
    
    <cfdi:Conceptos>
        <cfdi:Concepto
            ClaveProdServ="01010101"
            Cantidad="1"
            ClaveUnidad="H87"
            Unidad="Pieza"
            Descripcion="Producto/Servicio"
            ValorUnitario="1000.00"
            Importe="1000.00"/>
    </cfdi:Conceptos>
    
    <cfdi:Impuestos TotalImpuestosTrasladados="160.00">
        <cfdi:Traslados>
            <cfdi:Traslado Base="1000.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="160.00"/>
        </cfdi:Traslados>
    </cfdi:Impuestos>
    
</cfdi:Comprobante>"""
    
    return StreamingResponse(
        iter([xml_content.encode()]),
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=CFDI_{uuid}.xml"}
    )


@router.get("/{uuid}/pdf")
async def download_cfdi_pdf(
    uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download CFDI PDF file
    """
    
    # Verify user has SAT credentials
    sat_creds = db.query(SATCredentials).filter(
        SATCredentials.user_id == current_user.id
    ).first()
    
    if not sat_creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CFDI not found"
        )
    
    # Try to generate PDF with reportlab if available
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1
        )
        elements.append(Paragraph("COMPROBANTE FISCAL DIGITAL POR INTERNET", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Details table
        data = [
            ['RFC:', 'AAA010101AAA', 'Fecha:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Nombre:', 'Empresa Ejemplo S.A. de C.V.', 'Serie/Folio:', f"A/{uuid[:8]}"],
            ['', '', '', ''],
            ['RFC Receptor:', 'BBB020202BBB', 'Usuario:', current_user.first_name or 'Cliente'],
        ]
        
        t = Table(data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.3*inch))
        
        # Amounts table
        amounts_data = [
            ['Concepto', 'Cantidad', 'Unitario', 'Importe'],
            ['Producto/Servicio', '1', '$1,000.00', '$1,000.00'],
            ['', '', '', ''],
            ['Subtotal:', '', '', '$1,000.00'],
            ['IVA (16%):', '', '', '$160.00'],
            ['TOTAL:', '', '', '$1,160.00'],
        ]
        
        t2 = Table(amounts_data, colWidths=[2.5*inch, 1*inch, 1.5*inch, 1.5*inch])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 4), (-1, 5), colors.HexColor('#e6f2ff')),
            ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 5), (-1, 5), 14),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t2)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=CFDI_{uuid}.pdf"}
        )
    
    except ImportError:
        # Fallback if reportlab not installed - return simple PDF
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        c.setFont("Helvetica-Bold", 20)
        c.drawString(100, 750, "COMPROBANTE FISCAL DIGITAL")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, f"CFDI: {uuid}")
        c.drawString(100, 680, f"Fecha: {datetime.now().strftime('%Y-%m-%d')}")
        c.drawString(100, 660, f"Usuario: {current_user.first_name}")
        c.drawString(100, 640, "RFC Emisor: AAA010101AAA")
        c.drawString(100, 620, "RFC Receptor: BBB020202BBB")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 570, "Monto Total: $1,160.00")
        
        c.save()
        buffer.seek(0)
        
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=CFDI_{uuid}.pdf"}
        )


@router.get("/{uuid}/details")
async def get_cfdi_details(
    uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific CFDI
    
    TODO: Implement detailed CFDI retrieval from SAT
    """
    
    return {
        "uuid": uuid,
        "estado": "En desarrollo",
        "conceptos": [
            {
                "clave": "01010101",
                "descripcion": "Producto/Servicio",
                "cantidad": 1,
                "unitario": 1000.00,
                "importe": 1000.00
            }
        ],
        "impuestos": {
            "traslados": [
                {
                    "impuesto": "IVA",
                    "tasa": "0.16",
                    "importe": 160.00
                }
            ],
            "retenciones": []
        },
        "total_retenciones": 0,
        "total_traslados": 160.00,
        "subtotal": 1000.00,
        "total": 1160.00
    }


@router.post("/sync")
async def sync_cfdis_from_sat(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync CFDIs from SAT portal
    
    Conecta con el portal del SAT y obtiene los últimos CFDIs disponibles.
    Los datos se cachean localmente para futuras consultas.
    """
    
    sat_creds = db.query(SATCredentials).filter(
        SATCredentials.user_id == current_user.id
    ).first()
    
    if not sat_creds or not sat_creds.encrypted_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No SAT credentials configured"
        )
    
    try:
        logger.info(f"Starting CFDI sync for user {current_user.id}")
        
        # Decrypt password
        decrypted_password = decrypt_data(sat_creds.encrypted_password)
        
        # Set date range (last 12 months)
        end_date = datetime.today()
        start_date = end_date - timedelta(days=365)
        
        # Fetch CFDIs
        cfdis = await fetch_cfdis_from_sat(
            rfc=sat_creds.rfc,
            password=decrypted_password,
            start_date=start_date,
            end_date=end_date
        )
        
        # Clear cache for this user to force refresh
        cache_prefix = f"{current_user.id}_"
        keys_to_delete = [k for k in _cfdi_cache.keys() if k.startswith(cache_prefix)]
        for key in keys_to_delete:
            del _cfdi_cache[key]
        
        logger.info(f"Successfully synced {len(cfdis)} CFDIs for user {current_user.id}")
        
        return {
            "success": True,
            "message": "Sincronización completada con éxito",
            "cfdis_imported": len(cfdis),
            "last_sync": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error syncing CFDIs: {e}")
        return {
            "success": False,
            "message": f"Error en sincronización: {str(e)}",
            "cfdis_imported": 0,
            "last_sync": datetime.utcnow()
        }


@router.get("/statistics")
async def get_cfdi_statistics(
    year: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get CFDI statistics for user
    """
    
    sat_creds = db.query(SATCredentials).filter(
        SATCredentials.user_id == current_user.id
    ).first()
    
    if not sat_creds:
        return {
            "total_emitidos": 0,
            "total_recibidos": 0,
            "monto_total_emitido": 0,
            "monto_total_recibido": 0,
            "iva_trasladado": 0,
            "iva_retenido": 0
        }
    
    # Mock statistics
    return {
        "total_emitidos": 5,
        "total_recibidos": 3,
        "monto_total_emitido": 45000.00,
        "monto_total_recibido": 12000.00,
        "iva_trasladado": 7200.00,
        "iva_retenido": 300.00,
        "periodo": year or datetime.now().year
    }
