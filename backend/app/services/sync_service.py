"""
Sync Service - Orchestrates SAT data synchronization
Combines scraper, parser, and database operations
"""
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import os
import logging

from app.services.sat_scraper import SATScraper, SATScraperException
from app.services.cfdi_parser import CFDIParser
from app.models import User, CFDI, SATCredentials, FiscalProfile
from app.core.security import decrypt_password

logger = logging.getLogger(__name__)


class SyncStatus:
    """Track sync progress"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SATSyncService:
    """Service for synchronizing SAT data"""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.user = db.query(User).filter(User.id == user_id).first()
        
        if not self.user:
            raise ValueError(f"User {user_id} not found")
            
        # Get credentials
        self.credentials = db.query(SATCredentials).filter(
            SATCredentials.user_id == user_id
        ).first()
        
        if not self.credentials or not self.credentials.sat_password_encrypted:
            raise ValueError("SAT credentials not configured")
            
        # Get fiscal profile for RFC
        self.fiscal_profile = db.query(FiscalProfile).filter(
            FiscalProfile.user_id == user_id
        ).first()
        
        if not self.fiscal_profile or not self.fiscal_profile.rfc:
            raise ValueError("RFC not configured in fiscal profile")
            
    async def sync_all(self, months_back: int = 12) -> Dict:
        """
        Full sync - download and process all data
        
        Args:
            months_back: How many months back to sync
            
        Returns:
            Sync results summary
        """
        logger.info(f"Starting full sync for user {self.user_id}")
        
        results = {
            'status': SyncStatus.IN_PROGRESS,
            'started_at': datetime.now().isoformat(),
            'cfdis_downloaded': 0,
            'cfdis_processed': 0,
            'cfdis_skipped': 0,
            'errors': []
        }
        
        try:
            # Decrypt password
            password = decrypt_password(self.credentials.sat_password_encrypted)
            
            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=months_back * 30)
            
            # Create download directory
            download_dir = f"uploads/cfdis/{self.user_id}"
            os.makedirs(download_dir, exist_ok=True)
            
            # Initialize scraper
            async with SATScraper(
                rfc=self.fiscal_profile.rfc,
                password=password,
                headless=True
            ) as scraper:
                
                # Login
                logger.info("Logging into SAT portal")
                await scraper.login()
                
                # Download CFDIs
                logger.info(f"Downloading CFDIs from {start_date} to {end_date}")
                downloaded_cfdis = await scraper.download_cfdis(
                    start_date=start_date,
                    end_date=end_date,
                    download_dir=download_dir,
                    tipo="todos"
                )
                
                results['cfdis_downloaded'] = len(downloaded_cfdis)
                
                # Process each downloaded CFDI
                for cfdi_info in downloaded_cfdis:
                    try:
                        # Check if already exists
                        if cfdi_info.get('uuid'):
                            existing = self.db.query(CFDI).filter(
                                CFDI.uuid == cfdi_info['uuid'],
                                CFDI.user_id == self.user_id
                            ).first()
                            
                            if existing:
                                results['cfdis_skipped'] += 1
                                continue
                        
                        # Read XML
                        with open(cfdi_info['filepath'], 'r', encoding='utf-8') as f:
                            xml_content = f.read()
                        
                        # Parse CFDI
                        parser = CFDIParser(xml_content=xml_content)
                        cfdi_data = parser.parse()
                        
                        # Save to database (reuse logic from cfdis endpoint)
                        cfdi = self._create_cfdi_from_data(cfdi_data, cfdi_info['filepath'])
                        
                        self.db.add(cfdi)
                        self.db.commit()
                        
                        results['cfdis_processed'] += 1
                        logger.info(f"Processed CFDI: {cfdi.uuid}")
                        
                    except Exception as e:
                        logger.error(f"Error processing CFDI {cfdi_info.get('filename')}: {str(e)}")
                        results['errors'].append({
                            'file': cfdi_info.get('filename'),
                            'error': str(e)
                        })
                        continue
                
                # Download constancia fiscal
                try:
                    constancia_path = await scraper.get_constancia_fiscal(
                        download_dir=f"uploads/documents/{self.user_id}"
                    )
                    if constancia_path:
                        results['constancia_downloaded'] = True
                except Exception as e:
                    logger.warning(f"Could not download constancia: {str(e)}")
                    results['constancia_downloaded'] = False
                
            results['status'] = SyncStatus.COMPLETED
            results['completed_at'] = datetime.now().isoformat()
            
            logger.info(f"Sync completed: {results['cfdis_processed']} CFDIs processed")
            
        except SATScraperException as e:
            logger.error(f"Scraper error: {str(e)}")
            results['status'] = SyncStatus.FAILED
            results['error'] = str(e)
            
        except Exception as e:
            logger.error(f"Sync error: {str(e)}")
            results['status'] = SyncStatus.FAILED
            results['error'] = str(e)
            
        return results
        
    def _create_cfdi_from_data(self, cfdi_data: Dict, xml_path: str) -> CFDI:
        """Create CFDI model from parsed data"""
        from app.models import TipoComprobante, CFDIStatus
        from decimal import Decimal
        
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
            user_id=self.user_id,
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
            es_ingreso=cfdi_data['tipo_comprobante'] == 'I',
            es_egreso=cfdi_data['tipo_comprobante'] == 'E',
            es_nomina=cfdi_data['tipo_comprobante'] == 'N',
            es_deducible=self._is_deducible(cfdi_data),
            status=CFDIStatus.VIGENTE,
            conceptos=cfdi_data.get('conceptos'),
            impuestos_detalle=impuestos,
            timbre_data=cfdi_data.get('timbre'),
            xml_path=xml_path
        )
        
        return cfdi
        
    def _is_deducible(self, cfdi_data: Dict) -> bool:
        """Check if CFDI is tax deductible"""
        uso_cfdi = cfdi_data.get('receptor', {}).get('uso_cfdi', '')
        
        # Codigos de uso CFDI que son deducibles
        DEDUCIBLE_CODES = ['D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'D07', 'D08', 'D09', 'D10']
        
        return uso_cfdi in DEDUCIBLE_CODES
        
    async def sync_recent(self, days_back: int = 30) -> Dict:
        """
        Quick sync - only recent CFDIs
        
        Args:
            days_back: Number of days to sync
            
        Returns:
            Sync results
        """
        logger.info(f"Starting recent sync ({days_back} days) for user {self.user_id}")
        
        # Use sync_all with shorter range
        months = max(1, days_back // 30)
        return await self.sync_all(months_back=months)
        
    def get_last_sync_status(self) -> Optional[Dict]:
        """Get status of last sync operation"""
        # This would query a sync_history table if we had one
        # For now, return last CFDI update time
        last_cfdi = self.db.query(CFDI).filter(
            CFDI.user_id == self.user_id
        ).order_by(CFDI.created_at.desc()).first()
        
        if last_cfdi:
            return {
                'last_sync': last_cfdi.created_at.isoformat(),
                'total_cfdis': self.db.query(CFDI).filter(
                    CFDI.user_id == self.user_id
                ).count()
            }
            
        return None
