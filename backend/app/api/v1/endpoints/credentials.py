"""
API Endpoints - SAT Credentials Management
"""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from datetime import datetime
import os
import shutil

from app.core.database import get_db
from app.core.security import encrypt_data, decrypt_data
from app.models.user import User
from app.models.sat_credentials import SATCredentials
from app.schemas.sat import SATCredentialsCreate, SATCredentialsUpdate, SATConnectionTest
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter(prefix="/credentials", tags=["SAT Credentials"])

# Storage path for encrypted files
CREDENTIALS_STORAGE = "./storage/credentials"


def ensure_storage_exists():
    """Ensure storage directory exists"""
    os.makedirs(CREDENTIALS_STORAGE, exist_ok=True)


@router.get("/sat", status_code=200)
async def get_sat_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get SAT credentials status (non-sensitive data)"""
    
    credentials = db.query(SATCredentials).filter(
        SATCredentials.user_id == current_user.id
    ).first()
    
    if not credentials:
        return {
            "has_credentials": False,
            "has_password": False,
            "has_efirma": False,
            "efirma_expiry": None,
            "last_validated": None
        }
    
    return {
        "has_credentials": True,
        "has_password": credentials.encrypted_password is not None,
        "has_efirma": credentials.has_efirma,
        "efirma_expiry": credentials.efirma_expiry,
        "last_validated": credentials.last_validated
    }


@router.post("/sat", status_code=status.HTTP_201_CREATED)
async def save_sat_credentials(
    credentials_data: SATCredentialsCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save or update SAT password"""
    
    # Check if credentials already exist
    sat_creds = db.query(SATCredentials).filter(
        SATCredentials.user_id == current_user.id
    ).first()
    
    if sat_creds:
        # Update existing credentials
        sat_creds.encrypted_password = encrypt_data(credentials_data.sat_password)
        sat_creds.updated_at = datetime.utcnow()
    else:
        # Create new credentials
        sat_creds = SATCredentials(
            user_id=current_user.id,
            encrypted_password=encrypt_data(credentials_data.sat_password)
        )
        db.add(sat_creds)
    
    db.commit()
    db.refresh(sat_creds)
    
    return {
        "success": True,
        "message": "Credenciales guardadas correctamente",
        "has_password": True,
        "has_efirma": sat_creds.has_efirma,
        "last_updated": sat_creds.updated_at
    }


@router.put("/sat", status_code=200)
async def update_sat_credentials(
    credentials_data: SATCredentialsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update SAT credentials"""
    
    sat_creds = db.query(SATCredentials).filter(
        SATCredentials.user_id == current_user.id
    ).first()
    
    if not sat_creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No credentials found. Please create them first."
        )
    
    if credentials_data.sat_password:
        sat_creds.encrypted_password = encrypt_data(credentials_data.sat_password)
    
    sat_creds.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sat_creds)
    
    return {
        "success": True,
        "message": "Credenciales actualizadas correctamente",
        "last_updated": sat_creds.updated_at
    }


@router.post("/efirma/upload", status_code=status.HTTP_201_CREATED)
async def upload_efirma(
    cer_file: UploadFile = File(...),
    key_file: UploadFile = File(...),
    efirma_password: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload e.firma certificates (.cer and .key files)"""
    
    ensure_storage_exists()
    
    # Validate file extensions
    if not cer_file.filename.endswith('.cer'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CER file must have .cer extension"
        )
    
    if not key_file.filename.endswith('.key'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KEY file must have .key extension"
        )
    
    sat_creds = db.query(SATCredentials).filter(
        SATCredentials.user_id == current_user.id
    ).first()
    
    if not sat_creds:
        sat_creds = SATCredentials(user_id=current_user.id)
        db.add(sat_creds)
    
    try:
        # Create user-specific directory
        user_cred_dir = os.path.join(CREDENTIALS_STORAGE, f"user_{current_user.id}")
        os.makedirs(user_cred_dir, exist_ok=True)
        
        # Save CER file
        cer_path = os.path.join(user_cred_dir, f"certificate.cer")
        with open(cer_path, "wb") as buffer:
            shutil.copyfileobj(cer_file.file, buffer)
        
        # Save KEY file
        key_path = os.path.join(user_cred_dir, f"key.key")
        with open(key_path, "wb") as buffer:
            shutil.copyfileobj(key_file.file, buffer)
        
        # Update credentials
        sat_creds.efirma_cer_path = cer_path
        sat_creds.efirma_key_path = key_path
        sat_creds.has_efirma = True
        
        if efirma_password:
            sat_creds.encrypted_efirma_password = encrypt_data(efirma_password)
        
        sat_creds.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(sat_creds)
        
        return {
            "success": True,
            "message": "Certificados e.firma cargados correctamente",
            "has_efirma": True,
            "last_updated": sat_creds.updated_at
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading e.firma files: {str(e)}"
        )


@router.post("/test-connection")
async def test_sat_connection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test connection to SAT portal"""
    
    sat_creds = db.query(SATCredentials).filter(
        SATCredentials.user_id == current_user.id
    ).first()
    
    if not sat_creds or not sat_creds.encrypted_password:
        return SATConnectionTest(
            success=False,
            message="No SAT credentials configured",
            last_connection=None
        )
    
    # TODO: Implement actual SAT connection test
    # This would use the automation service to test the connection
    
    return SATConnectionTest(
        success=True,
        message="Conexión a SAT - Funcionalidad en desarrollo",
        last_connection=datetime.utcnow()
    )


@router.delete("/sat", status_code=200)
async def delete_sat_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete SAT credentials"""
    
    sat_creds = db.query(SATCredentials).filter(
        SATCredentials.user_id == current_user.id
    ).first()
    
    if not sat_creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No credentials found"
        )
    
    # Delete uploaded files
    try:
        user_cred_dir = os.path.join(CREDENTIALS_STORAGE, f"user_{current_user.id}")
        if os.path.exists(user_cred_dir):
            shutil.rmtree(user_cred_dir)
    except Exception as e:
        # Log but don't fail
        print(f"Error deleting credential files: {str(e)}")
    
    # Delete from database
    db.delete(sat_creds)
    db.commit()
    
    return {
        "success": True,
        "message": "Credenciales eliminadas correctamente"
    }
