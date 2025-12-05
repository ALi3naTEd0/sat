"""
Database Models - CFDI
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Numeric, JSON, Index, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
from decimal import Decimal


class TipoComprobante(str, enum.Enum):
    """Tipo de comprobante CFDI"""
    INGRESO = "I"  # Factura de ingreso
    EGRESO = "E"   # Nota de crédito
    TRASLADO = "T" # Carta porte
    NOMINA = "N"   # Recibo de nómina
    PAGO = "P"     # Complemento de pago


class CFDIStatus(str, enum.Enum):
    """Estado del CFDI"""
    VIGENTE = "vigente"
    CANCELADO = "cancelado"
    PENDIENTE = "pendiente"


class CFDI(Base):
    """Modelo para almacenar CFDIs (Comprobante Fiscal Digital por Internet)"""
    __tablename__ = "cfdis"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Usuario propietario
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Identificadores únicos
    uuid = Column(String(36), unique=True, nullable=False, index=True)  # Folio fiscal
    serie = Column(String(25))
    folio = Column(String(40))
    
    # Versión y tipo
    version = Column(String(5))  # 3.3 o 4.0
    tipo_comprobante = Column(SQLEnum(TipoComprobante), nullable=False, index=True)
    
    # Fechas
    fecha_emision = Column(DateTime(timezone=True), nullable=False, index=True)
    fecha_timbrado = Column(DateTime(timezone=True), nullable=False)
    fecha_certificacion = Column(DateTime(timezone=True))
    
    # Emisor
    emisor_rfc = Column(String(13), nullable=False, index=True)
    emisor_nombre = Column(String(254))
    emisor_regimen_fiscal = Column(String(10))
    
    # Receptor
    receptor_rfc = Column(String(13), nullable=False, index=True)
    receptor_nombre = Column(String(254))
    receptor_domicilio_fiscal = Column(String(5))
    receptor_regimen_fiscal = Column(String(10))
    receptor_uso_cfdi = Column(String(5), index=True)  # Para clasificar deducciones
    
    # Montos
    moneda = Column(String(3), default="MXN")
    tipo_cambio = Column(Numeric(10, 6), default=1.0)
    subtotal = Column(Numeric(18, 6), nullable=False)
    descuento = Column(Numeric(18, 6), default=0)
    total = Column(Numeric(18, 6), nullable=False)
    
    # Impuestos
    total_impuestos_trasladados = Column(Numeric(18, 6), default=0)
    total_impuestos_retenidos = Column(Numeric(18, 6), default=0)
    iva_trasladado = Column(Numeric(18, 6), default=0)
    isr_retenido = Column(Numeric(18, 6), default=0)
    
    # Método y forma de pago
    metodo_pago = Column(String(10))  # PUE, PPD
    forma_pago = Column(String(10))   # 01, 03, 28, etc
    
    # Clasificación
    es_ingreso = Column(Boolean, default=False, index=True)
    es_egreso = Column(Boolean, default=False, index=True)
    es_nomina = Column(Boolean, default=False, index=True)
    es_deducible = Column(Boolean, default=False, index=True)
    
    # Estado
    status = Column(SQLEnum(CFDIStatus), default=CFDIStatus.VIGENTE, index=True)
    
    # Datos completos en JSON
    conceptos = Column(JSON)  # Lista de conceptos
    impuestos_detalle = Column(JSON)  # Detalle de impuestos
    timbre_data = Column(JSON)  # Datos del timbre
    complementos = Column(JSON)  # Complementos adicionales
    
    # Archivos
    xml_path = Column(String(512))  # Ruta al archivo XML
    xml_content = Column(String)  # Contenido completo del XML (para Web Services)
    pdf_path = Column(String(512))  # Ruta al PDF (si existe)
    
    # Metadata
    doc_metadata = Column(JSON)  # Metadata adicional
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    user = relationship("User", back_populates="cfdis")
    
    # Índices compuestos para búsquedas comunes
    __table_args__ = (
        Index('idx_user_fecha', 'user_id', 'fecha_emision'),
        Index('idx_user_tipo', 'user_id', 'tipo_comprobante'),
        Index('idx_user_deducible', 'user_id', 'es_deducible'),
        Index('idx_receptor_fecha', 'receptor_rfc', 'fecha_emision'),
        Index('idx_emisor_fecha', 'emisor_rfc', 'fecha_emision'),
    )
    
    def __repr__(self):
        return f"<CFDI {self.uuid} - {self.emisor_nombre} - ${self.total}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'serie': self.serie,
            'folio': self.folio,
            'tipo_comprobante': self.tipo_comprobante.value if self.tipo_comprobante else None,
            'fecha_emision': self.fecha_emision.isoformat() if self.fecha_emision else None,
            'emisor': {
                'rfc': self.emisor_rfc,
                'nombre': self.emisor_nombre,
                'regimen_fiscal': self.emisor_regimen_fiscal
            },
            'receptor': {
                'rfc': self.receptor_rfc,
                'nombre': self.receptor_nombre,
                'uso_cfdi': self.receptor_uso_cfdi
            },
            'montos': {
                'moneda': self.moneda,
                'subtotal': float(self.subtotal) if self.subtotal else 0,
                'descuento': float(self.descuento) if self.descuento else 0,
                'total': float(self.total) if self.total else 0,
                'iva': float(self.iva_trasladado) if self.iva_trasladado else 0,
                'isr_retenido': float(self.isr_retenido) if self.isr_retenido else 0
            },
            'conceptos': self.conceptos,
            'status': self.status.value if self.status else None,
            'es_deducible': self.es_deducible,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PrestacionAnual(Base):
    """Modelo para almacenar cálculos de prestaciones anuales"""
    __tablename__ = "prestaciones_anuales"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    
    # Ingresos
    total_ingresos = Column(Numeric(18, 2), default=0)
    ingresos_sueldos = Column(Numeric(18, 2), default=0)
    ingresos_actividad_empresarial = Column(Numeric(18, 2), default=0)
    ingresos_arrendamiento = Column(Numeric(18, 2), default=0)
    ingresos_intereses = Column(Numeric(18, 2), default=0)
    otros_ingresos = Column(Numeric(18, 2), default=0)
    
    # Deducciones autorizadas
    total_deducciones = Column(Numeric(18, 2), default=0)
    gastos_medicos = Column(Numeric(18, 2), default=0)
    intereses_hipotecarios = Column(Numeric(18, 2), default=0)
    educacion = Column(Numeric(18, 2), default=0)
    seguros = Column(Numeric(18, 2), default=0)
    transporte_escolar = Column(Numeric(18, 2), default=0)
    donativos = Column(Numeric(18, 2), default=0)
    otras_deducciones = Column(Numeric(18, 2), default=0)
    
    # Impuestos
    isr_retenido = Column(Numeric(18, 2), default=0)
    isr_pagado = Column(Numeric(18, 2), default=0)
    iva_pagado = Column(Numeric(18, 2), default=0)
    
    # Resultado
    base_gravable = Column(Numeric(18, 2), default=0)
    
    # Metadata
    total_cfdis = Column(Integer, default=0)
    ultimo_calculo = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    user = relationship("User", back_populates="prestaciones")
    
    __table_args__ = (
        Index('idx_user_year', 'user_id', 'year', unique=True),
    )
    
    def __repr__(self):
        return f"<Prestacion {self.year} - User {self.user_id}>"
