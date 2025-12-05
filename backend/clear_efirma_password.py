#!/usr/bin/env python
"""
Script para limpiar contraseña de e.firma corrupta
Ejecutar si tienes error InvalidToken al sincronizar
"""
from app.core.database import SessionLocal
from app.models import SATCredentials

def clear_efirma_password(user_id: int):
    """Clear corrupted e.firma password for a user"""
    db = SessionLocal()
    try:
        creds = db.query(SATCredentials).filter(
            SATCredentials.user_id == user_id
        ).first()
        
        if creds:
            creds.encrypted_efirma_password = None
            db.commit()
            print(f"✅ Contraseña e.firma limpiada para usuario {user_id}")
            print("⚠️  Necesitas volver a subir tu contraseña en Credenciales SAT")
        else:
            print(f"❌ No se encontraron credenciales para usuario {user_id}")
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Uso: python clear_efirma_password.py <user_id>")
        sys.exit(1)
    
    user_id = int(sys.argv[1])
    clear_efirma_password(user_id)
