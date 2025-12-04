"""
Update database schema - Add CFDI and Prestaciones tables
Run this to add the new tables to existing database
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from app.core.database import engine, Base
from app.models import CFDI, PrestacionAnual

def update_tables():
    """Create new CFDI and Prestaciones tables"""
    print("📊 Actualizando esquema de base de datos...")
    print("Agregando tablas: cfdis, prestaciones_anuales")
    
    try:
        # Create only the new tables
        Base.metadata.create_all(bind=engine, tables=[
            CFDI.__table__,
            PrestacionAnual.__table__
        ])
        
        print("✅ Tablas creadas exitosamente")
        print("\nTablas agregadas:")
        print("  - cfdis: Almacenamiento de CFDIs")
        print("  - prestaciones_anuales: Cálculos de prestaciones anuales")
        
    except Exception as e:
        print(f"❌ Error al crear tablas: {e}")
        raise

if __name__ == "__main__":
    update_tables()
