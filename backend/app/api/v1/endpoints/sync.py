"""
Sync Endpoints - API routes for SAT data synchronization
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models import User
from app.services.sync_service import SATSyncService

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncRequest(BaseModel):
    months_back: Optional[int] = 12
    force: Optional[bool] = False


class SyncResponse(BaseModel):
    message: str
    sync_id: Optional[str] = None
    status: str


@router.post("/start", response_model=SyncResponse)
async def start_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start SAT data synchronization
    
    Downloads CFDIs and declarations from SAT portal automatically.
    Requires SAT credentials to be configured.
    
    - **months_back**: How many months to sync (default: 12)
    - **force**: Force resync even if data exists
    """
    try:
        # Check if credentials exist
        from app.models import SATCredentials, FiscalProfile
        
        credentials = db.query(SATCredentials).filter(
            SATCredentials.user_id == current_user.id
        ).first()
        
        if not credentials or not credentials.encrypted_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credenciales SAT no configuradas. Ve a la sección 'Credenciales SAT' primero."
            )
            
        fiscal_profile = db.query(FiscalProfile).filter(
            FiscalProfile.user_id == current_user.id
        ).first()
        
        if not fiscal_profile or not fiscal_profile.rfc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RFC no configurado. Completa tu perfil fiscal primero."
            )
        
        # Initialize sync service
        sync_service = SATSyncService(db, current_user.id)
        
        # Start sync in background
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)
        
        async def run_sync():
            try:
                logger.info(f"Starting sync for user {current_user.id}")
                results = await sync_service.sync_all(months_back=request.months_back)
                logger.info(f"Sync completed successfully: {results}")
            except Exception as e:
                logger.error(f"Sync error for user {current_user.id}: {str(e)}", exc_info=True)
                # Error is already saved in sync_service.sync_all()
        
        # Add to background tasks
        background_tasks.add_task(lambda: asyncio.run(run_sync()))
        
        return SyncResponse(
            message="Sincronización iniciada en segundo plano",
            status="started"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al iniciar sincronización: {str(e)}"
        )


@router.get("/status")
def get_sync_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get synchronization status
    
    Returns info about last sync and data statistics including:
    - Current sync status (running/completed/failed)
    - When it started and finished
    - How many CFDIs were downloaded
    - Breakdown of emitidos vs recibidos
    - Total amounts (ingresos/egresos)
    """
    try:
        sync_service = SATSyncService(db, current_user.id)
        status_info = sync_service.get_last_sync_status()
        
        if not status_info:
            return {
                'has_synced': False,
                'message': 'Aún no has sincronizado datos del SAT'
            }
            
        return {
            'has_synced': True,
            **status_info
        }
        
    except ValueError as e:
        # Credentials not configured
        return {
            'has_synced': False,
            'message': 'Configura tus credenciales SAT primero',
            'needs_config': True
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estado: {str(e)}"
        )


@router.post("/quick")
async def quick_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Quick sync - only last 30 days
    
    Faster sync for recent data updates
    """
    try:
        sync_service = SATSyncService(db, current_user.id)
        
        # Start quick sync in background
        import asyncio
        
        async def run_quick_sync():
            try:
                results = await sync_service.sync_recent(days_back=30)
                print(f"Quick sync completed: {results}")
            except Exception as e:
                print(f"Quick sync error: {str(e)}")
        
        background_tasks.add_task(lambda: asyncio.run(run_quick_sync()))
        
        return {
            'message': 'Sincronización rápida iniciada (últimos 30 días)',
            'status': 'started'
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )
