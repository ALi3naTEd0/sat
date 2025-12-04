"""
Prestaciones Calculator Service
Calculate annual income, deductions and prestaciones from CFDIs
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from typing import Dict, List
from decimal import Decimal
from datetime import datetime

from app.models import CFDI, PrestacionAnual, User


class PrestacionesCalculator:
    """Calculate prestaciones and deductions from CFDIs"""
    
    # Uso CFDI codes for deductions
    DEDUCCION_CODES = {
        'D01': 'gastos_medicos',  # Honorarios médicos
        'D02': 'gastos_medicos',  # Gastos médicos por incapacidad
        'D03': 'otras_deducciones',  # Gastos funerales
        'D04': 'donativos',  # Donativos
        'D05': 'intereses_hipotecarios',  # Intereses hipotecarios
        'D06': 'otras_deducciones',  # Aportaciones SAR
        'D07': 'seguros',  # Seguros gastos médicos
        'D08': 'transporte_escolar',  # Transporte escolar
        'D09': 'otras_deducciones',  # Ahorro
        'D10': 'educacion',  # Servicios educativos
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_year(self, user_id: int, year: int) -> PrestacionAnual:
        """
        Calculate prestaciones for a specific year
        Updates or creates PrestacionAnual record
        """
        # Get all CFDIs for the year
        cfdis = self.db.query(CFDI).filter(
            CFDI.user_id == user_id,
            extract('year', CFDI.fecha_emision) == year,
            CFDI.status == 'vigente'
        ).all()
        
        # Initialize totals
        ingresos = {
            'total': Decimal('0'),
            'sueldos': Decimal('0'),
            'empresarial': Decimal('0'),
            'arrendamiento': Decimal('0'),
            'intereses': Decimal('0'),
            'otros': Decimal('0')
        }
        
        deducciones = {
            'total': Decimal('0'),
            'gastos_medicos': Decimal('0'),
            'intereses_hipotecarios': Decimal('0'),
            'educacion': Decimal('0'),
            'seguros': Decimal('0'),
            'transporte_escolar': Decimal('0'),
            'donativos': Decimal('0'),
            'otras': Decimal('0')
        }
        
        impuestos = {
            'isr_retenido': Decimal('0'),
            'isr_pagado': Decimal('0'),
            'iva_pagado': Decimal('0')
        }
        
        # Process each CFDI
        for cfdi in cfdis:
            if cfdi.es_nomina:
                # Payroll income
                ingresos['sueldos'] += cfdi.total
                impuestos['isr_retenido'] += cfdi.isr_retenido or Decimal('0')
            
            elif cfdi.es_ingreso:
                # Business or other income
                # Could be categorized based on conceptos
                ingresos['empresarial'] += cfdi.total
            
            elif cfdi.es_deducible:
                # Deductible expense
                uso_cfdi = cfdi.receptor_uso_cfdi
                
                if uso_cfdi in self.DEDUCCION_CODES:
                    field = self.DEDUCCION_CODES[uso_cfdi]
                    deducciones[field] += cfdi.total
                else:
                    deducciones['otras'] += cfdi.total
        
        # Calculate totals
        ingresos['total'] = sum(ingresos.values()) - ingresos['total']  # Exclude 'total' from sum
        deducciones['total'] = sum(deducciones.values()) - deducciones['total']
        
        # Calculate base gravable
        base_gravable = ingresos['total'] - deducciones['total']
        
        # Get or create PrestacionAnual record
        prestacion = self.db.query(PrestacionAnual).filter(
            PrestacionAnual.user_id == user_id,
            PrestacionAnual.year == year
        ).first()
        
        if not prestacion:
            prestacion = PrestacionAnual(
                user_id=user_id,
                year=year
            )
            self.db.add(prestacion)
        
        # Update values
        prestacion.total_ingresos = ingresos['total']
        prestacion.ingresos_sueldos = ingresos['sueldos']
        prestacion.ingresos_actividad_empresarial = ingresos['empresarial']
        prestacion.ingresos_arrendamiento = ingresos['arrendamiento']
        prestacion.ingresos_intereses = ingresos['intereses']
        prestacion.otros_ingresos = ingresos['otros']
        
        prestacion.total_deducciones = deducciones['total']
        prestacion.gastos_medicos = deducciones['gastos_medicos']
        prestacion.intereses_hipotecarios = deducciones['intereses_hipotecarios']
        prestacion.educacion = deducciones['educacion']
        prestacion.seguros = deducciones['seguros']
        prestacion.transporte_escolar = deducciones['transporte_escolar']
        prestacion.donativos = deducciones['donativos']
        prestacion.otras_deducciones = deducciones['otras']
        
        prestacion.isr_retenido = impuestos['isr_retenido']
        prestacion.isr_pagado = impuestos['isr_pagado']
        prestacion.iva_pagado = impuestos['iva_pagado']
        
        prestacion.base_gravable = base_gravable
        prestacion.total_cfdis = len(cfdis)
        prestacion.ultimo_calculo = datetime.now()
        
        self.db.commit()
        self.db.refresh(prestacion)
        
        return prestacion
    
    def get_monthly_breakdown(self, user_id: int, year: int) -> List[Dict]:
        """
        Get monthly income breakdown for a year
        """
        monthly_data = []
        
        for month in range(1, 13):
            # Get CFDIs for this month
            cfdis = self.db.query(CFDI).filter(
                CFDI.user_id == user_id,
                extract('year', CFDI.fecha_emision) == year,
                extract('month', CFDI.fecha_emision) == month,
                CFDI.status == 'vigente'
            ).all()
            
            # Calculate totals
            ingresos = sum(cfdi.total for cfdi in cfdis if cfdi.es_ingreso or cfdi.es_nomina)
            isr_retenido = sum(cfdi.isr_retenido or Decimal('0') for cfdi in cfdis if cfdi.es_nomina)
            
            monthly_data.append({
                'month': month,
                'ingresos': float(ingresos),
                'isr_retenido': float(isr_retenido),
                'total_cfdis': len(cfdis)
            })
        
        return monthly_data
    
    def get_deduction_breakdown(self, user_id: int, year: int) -> Dict[str, float]:
        """
        Get detailed breakdown of deductions by category
        """
        deducible_cfdis = self.db.query(CFDI).filter(
            CFDI.user_id == user_id,
            extract('year', CFDI.fecha_emision) == year,
            CFDI.es_deducible == True,
            CFDI.status == 'vigente'
        ).all()
        
        breakdown = {
            'gastos_medicos': [],
            'intereses_hipotecarios': [],
            'educacion': [],
            'seguros': [],
            'transporte_escolar': [],
            'donativos': [],
            'otras_deducciones': []
        }
        
        for cfdi in deducible_cfdis:
            uso_cfdi = cfdi.receptor_uso_cfdi
            category = self.DEDUCCION_CODES.get(uso_cfdi, 'otras_deducciones')
            
            breakdown[category].append({
                'uuid': cfdi.uuid,
                'fecha': cfdi.fecha_emision.isoformat(),
                'emisor': cfdi.emisor_nombre,
                'total': float(cfdi.total),
                'uso_cfdi': uso_cfdi
            })
        
        return breakdown


def calculate_prestaciones(db: Session, user_id: int, year: int) -> PrestacionAnual:
    """Convenience function to calculate prestaciones"""
    calculator = PrestacionesCalculator(db)
    return calculator.calculate_year(user_id, year)
