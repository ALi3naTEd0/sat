"""
Declaraciones Service - Calculates and manages tax declarations
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional
import calendar

from app.models import User, CFDI, PrestacionAnual, FiscalProfile, Document, DocumentType


class DeclaracionesService:
    """Service for calculating tax declarations from CFDIs"""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.user = db.query(User).filter(User.id == user_id).first()
        if not self.user:
            raise ValueError(f"User {user_id} not found")
    
    def get_declaracion_mensual(self, year: int, month: int) -> Dict:
        """
        Calculate monthly tax declaration
        Similar to what SAT sends via email
        """
        # Get all CFDIs for the month
        cfdis = self.db.query(CFDI).filter(
            and_(
                CFDI.user_id == self.user_id,
                extract('year', CFDI.fecha_emision) == year,
                extract('month', CFDI.fecha_emision) == month
            )
        ).all()
        
        # Initialize totals
        ingresos_totales = Decimal('0')
        ingresos_gravados = Decimal('0')
        ingresos_exentos = Decimal('0')
        
        egresos_totales = Decimal('0')
        egresos_deducibles = Decimal('0')
        
        iva_cobrado = Decimal('0')
        iva_pagado = Decimal('0')
        isr_retenido = Decimal('0')
        
        # Nomina data
        salarios_totales = Decimal('0')
        isr_nomina = Decimal('0')
        
        # Process each CFDI
        for cfdi in cfdis:
            if cfdi.es_ingreso:
                ingresos_totales += cfdi.total
                # Consider tax regime for gravable/exempt split
                ingresos_gravados += cfdi.subtotal
                iva_cobrado += cfdi.iva_trasladado
                
            elif cfdi.es_egreso:
                egresos_totales += cfdi.total
                if cfdi.es_deducible:
                    egresos_deducibles += cfdi.subtotal
                    iva_pagado += cfdi.iva_trasladado
                    
            elif cfdi.es_nomina:
                salarios_totales += cfdi.total
                isr_nomina += cfdi.isr_retenido
        
        # Calculate net IVA
        iva_neto = iva_cobrado - iva_pagado
        iva_a_cargo = iva_neto if iva_neto > 0 else Decimal('0')
        iva_a_favor = abs(iva_neto) if iva_neto < 0 else Decimal('0')
        
        # Calculate ISR (simplified)
        utilidad_bruta = ingresos_gravados - egresos_deducibles
        # This is simplified - real ISR calculation needs tax tables
        base_isr = utilidad_bruta if utilidad_bruta > 0 else Decimal('0')
        
        # Get fiscal profile for regime
        fiscal_profile = self.db.query(FiscalProfile).filter(
            FiscalProfile.user_id == self.user_id
        ).first()
        
        return {
            'periodo': {
                'year': year,
                'month': month,
                'month_name': calendar.month_name[month],
                'periodo_texto': f"{calendar.month_name[month]} {year}"
            },
            'contribuyente': {
                'rfc': fiscal_profile.rfc if fiscal_profile else None,
                'nombre': fiscal_profile.legal_name if fiscal_profile else None,
                'regimen': fiscal_profile.tax_regime.value if fiscal_profile and fiscal_profile.tax_regime else None
            },
            'ingresos': {
                'totales': float(ingresos_totales),
                'gravados': float(ingresos_gravados),
                'exentos': float(ingresos_exentos),
                'iva_cobrado': float(iva_cobrado)
            },
            'egresos': {
                'totales': float(egresos_totales),
                'deducibles': float(egresos_deducibles),
                'iva_pagado': float(iva_pagado)
            },
            'nomina': {
                'salarios': float(salarios_totales),
                'isr_retenido': float(isr_nomina)
            },
            'impuestos': {
                'iva': {
                    'cobrado': float(iva_cobrado),
                    'pagado': float(iva_pagado),
                    'neto': float(iva_neto),
                    'a_cargo': float(iva_a_cargo),
                    'a_favor': float(iva_a_favor)
                },
                'isr': {
                    'base': float(base_isr),
                    'retenido': float(isr_nomina),
                    # Real calculation would go here
                    'causado': 0,
                    'a_cargo': 0,
                    'a_favor': 0
                }
            },
            'resumen': {
                'utilidad_bruta': float(utilidad_bruta),
                'total_impuestos_cargo': float(iva_a_cargo),
                'total_impuestos_favor': float(iva_a_favor)
            },
            'cfdis_count': {
                'ingresos': sum(1 for c in cfdis if c.es_ingreso),
                'egresos': sum(1 for c in cfdis if c.es_egreso),
                'nominas': sum(1 for c in cfdis if c.es_nomina),
                'total': len(cfdis)
            },
            'fecha_calculo': datetime.now().isoformat()
        }
    
    def get_declaracion_anual(self, year: int) -> Dict:
        """
        Calculate annual tax declaration
        """
        # Get yearly summary from prestaciones
        prestacion = self.db.query(PrestacionAnual).filter(
            and_(
                PrestacionAnual.user_id == self.user_id,
                PrestacionAnual.year == year
            )
        ).first()
        
        if not prestacion:
            # Calculate it
            from app.services.prestaciones_calculator import PrestacionesCalculator
            calc = PrestacionesCalculator(self.db, self.user_id)
            prestacion = calc.calculate_year(year)
        
        # Get fiscal profile
        fiscal_profile = self.db.query(FiscalProfile).filter(
            FiscalProfile.user_id == self.user_id
        ).first()
        
        # Calculate total deductions
        total_deducciones = sum([
            prestacion.deducciones_medicas or Decimal('0'),
            prestacion.deducciones_dentales or Decimal('0'),
            prestacion.deducciones_hospitalarios or Decimal('0'),
            prestacion.deducciones_funerarios or Decimal('0'),
            prestacion.deducciones_donativos or Decimal('0'),
            prestacion.deducciones_intereses or Decimal('0'),
            prestacion.deducciones_seguros or Decimal('0'),
            prestacion.deducciones_transporte or Decimal('0'),
            prestacion.deducciones_educacion or Decimal('0'),
            prestacion.deducciones_otras or Decimal('0')
        ])
        
        return {
            'ejercicio': year,
            'contribuyente': {
                'rfc': fiscal_profile.rfc if fiscal_profile else None,
                'nombre': fiscal_profile.legal_name if fiscal_profile else None,
                'regimen': fiscal_profile.tax_regime.value if fiscal_profile and fiscal_profile.tax_regime else None,
                'curp': fiscal_profile.curp if fiscal_profile else None
            },
            'ingresos': {
                'salarios_nomina': float(prestacion.ingresos_salarios or 0),
                'honorarios': float(prestacion.ingresos_honorarios or 0),
                'arrendamiento': float(prestacion.ingresos_arrendamiento or 0),
                'actividad_empresarial': float(prestacion.ingresos_actividad_empresarial or 0),
                'intereses': float(prestacion.ingresos_intereses or 0),
                'otros': float(prestacion.ingresos_otros or 0),
                'total': float(prestacion.ingresos_totales or 0)
            },
            'deducciones': {
                'medicas': float(prestacion.deducciones_medicas or 0),
                'dentales': float(prestacion.deducciones_dentales or 0),
                'hospitalarios': float(prestacion.deducciones_hospitalarios or 0),
                'funerarios': float(prestacion.deducciones_funerarios or 0),
                'donativos': float(prestacion.deducciones_donativos or 0),
                'intereses_hipotecarios': float(prestacion.deducciones_intereses or 0),
                'seguros_medicos': float(prestacion.deducciones_seguros or 0),
                'transporte_escolar': float(prestacion.deducciones_transporte or 0),
                'educacion': float(prestacion.deducciones_educacion or 0),
                'otras': float(prestacion.deducciones_otras or 0),
                'total': float(total_deducciones)
            },
            'impuestos': {
                'isr': {
                    'retenido': float(prestacion.isr_retenido or 0),
                    'causado': float(prestacion.isr_causado or 0),
                    'a_cargo': float(prestacion.isr_cargo or 0),
                    'a_favor': float(prestacion.isr_favor or 0)
                },
                'base_gravable': float(prestacion.base_gravable or 0)
            },
            'resumen': {
                'ingresos_acumulables': float(prestacion.ingresos_totales or 0),
                'deducciones_autorizadas': float(total_deducciones),
                'base_gravable': float(prestacion.base_gravable or 0),
                'isr_cargo_favor': float((prestacion.isr_favor or 0) - (prestacion.isr_cargo or 0))
            },
            'fecha_calculo': datetime.now().isoformat()
        }
    
    def get_resumen_declaraciones(self, year: int) -> Dict:
        """
        Get summary of all declarations for a year
        """
        declaraciones_mensuales = []
        
        for month in range(1, 13):
            decl = self.get_declaracion_mensual(year, month)
            declaraciones_mensuales.append({
                'mes': month,
                'mes_nombre': calendar.month_name[month],
                'ingresos': decl['ingresos']['totales'],
                'egresos': decl['egresos']['totales'],
                'iva_neto': decl['impuestos']['iva']['neto'],
                'cfdis': decl['cfdis_count']['total']
            })
        
        declaracion_anual = self.get_declaracion_anual(year)
        
        return {
            'year': year,
            'declaraciones_mensuales': declaraciones_mensuales,
            'declaracion_anual': declaracion_anual,
            'totales': {
                'ingresos_anuales': declaracion_anual['ingresos']['total'],
                'deducciones_anuales': declaracion_anual['deducciones']['total'],
                'isr_total': declaracion_anual['impuestos']['isr']['causado'],
                'saldo_final': declaracion_anual['resumen']['isr_cargo_favor']
            }
        }
