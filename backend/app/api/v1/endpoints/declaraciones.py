"""
Declaraciones Endpoints - API routes for tax declarations
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models import User
from app.services.declaraciones_service import DeclaracionesService

router = APIRouter(prefix="/declaraciones", tags=["declaraciones"])


@router.get("/mensual/{year}/{month}")
def get_declaracion_mensual(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get monthly tax declaration (similar to SAT email notifications)
    
    Returns calculated values for:
    - Income (ingresos)
    - Expenses (egresos)  
    - IVA (charged and paid)
    - ISR (retained)
    - Summary of CFDIs used
    """
    try:
        service = DeclaracionesService(db, current_user.id)
        declaracion = service.get_declaracion_mensual(year, month)
        return declaracion
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calcular declaración: {str(e)}"
        )


@router.get("/anual/{year}")
def get_declaracion_anual(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get annual tax declaration
    
    Returns complete annual tax information including:
    - All income sources
    - All authorized deductions
    - ISR calculation
    - Final balance (charge or favor)
    """
    try:
        service = DeclaracionesService(db, current_user.id)
        declaracion = service.get_declaracion_anual(year)
        return declaracion
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calcular declaración: {str(e)}"
        )


@router.get("/resumen/{year}")
def get_resumen_declaraciones(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary of all declarations for the year
    
    Returns:
    - Monthly declarations summary
    - Annual declaration
    - Year totals
    """
    try:
        service = DeclaracionesService(db, current_user.id)
        resumen = service.get_resumen_declaraciones(year)
        return resumen
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar resumen: {str(e)}"
        )


@router.get("/disponibles")
def get_declaraciones_disponibles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available declaration periods
    
    Returns years and months with CFDI data
    """
    from sqlalchemy import func, extract
    from app.models import CFDI
    
    # Get distinct years and months with CFDIs
    periodos = db.query(
        extract('year', CFDI.fecha_emision).label('year'),
        extract('month', CFDI.fecha_emision).label('month')
    ).filter(
        CFDI.user_id == current_user.id
    ).distinct().order_by(
        extract('year', CFDI.fecha_emision).desc(),
        extract('month', CFDI.fecha_emision).desc()
    ).all()
    
    import calendar
    
    # Group by year
    years_dict = {}
    for periodo in periodos:
        year = int(periodo.year)
        month = int(periodo.month)
        
        if year not in years_dict:
            years_dict[year] = {
                'year': year,
                'meses': []
            }
        
        years_dict[year]['meses'].append({
            'mes': month,
            'mes_nombre': calendar.month_name[month]
        })
    
    return {
        'periodos_disponibles': list(years_dict.values())
    }
