"""
Sync Service - Orchestrates SAT data synchronization using Web Services
Uses official SAT SOAP APIs with e.firma authentication
"""
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import os
import logging

from app.services.sat_webservice_client import SATWebServiceClient, TipoDescarga
from app.services.efirma_service import EfirmaService
from app.services.paquete_processor import PaqueteProcessor
from app.services.cfdi_parser import CFDIParser
from app.models import User, CFDI, SATCredentials, FiscalProfile, SyncHistory, SyncStatus, SyncType

logger = logging.getLogger(__name__)


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
        
        if not self.credentials:
            raise ValueError("SAT credentials not configured")
            
        # Get fiscal profile for RFC
        self.fiscal_profile = db.query(FiscalProfile).filter(
            FiscalProfile.user_id == user_id
        ).first()
        
        if not self.fiscal_profile or not self.fiscal_profile.rfc:
            raise ValueError("RFC not configured. Complete your fiscal profile first.")
        
        # Check e.firma files
        if not self.credentials.efirma_cer_path or not self.credentials.efirma_key_path:
            raise ValueError(
                "e.firma files not uploaded. Please upload your .cer and .key files "
                "in the Credentials section."
            )
            
    async def sync_all(self, months_back: int = 12) -> Dict:
        """
        Full sync - download and process all data
        
        Args:
            months_back: How many months back to sync
            
        Returns:
            Sync results summary
        """
        logger.info(f"Starting full sync for user {self.user_id}")
        
        # Create sync history record
        sync_record = SyncHistory(
            user_id=self.user_id,
            sync_type=SyncType.FULL,
            status=SyncStatus.RUNNING,
            months_back=months_back
        )
        self.db.add(sync_record)
        self.db.commit()
        self.db.refresh(sync_record)
        
        results = {
            'sync_id': sync_record.id,
            'status': SyncStatus.RUNNING,
            'started_at': sync_record.started_at.isoformat(),
            'cfdis_downloaded': 0,
            'cfdis_processed': 0,
            'cfdis_skipped': 0,
            'cfdis_emitidos': 0,
            'cfdis_recibidos': 0,
            'total_ingresos': 0.0,
            'total_egresos': 0.0,
            'errors': []
        }
        
        try:
            # Decrypt e.firma password
            from app.core.security import decrypt_data
            
            if not self.credentials.encrypted_efirma_password:
                raise ValueError(
                    "e.firma password not configured. Please upload your e.firma files "
                    "and password in the Credentials section."
                )
            
            try:
                efirma_password = decrypt_data(self.credentials.encrypted_efirma_password)
            except Exception as decrypt_error:
                logger.error(f"Failed to decrypt e.firma password: {decrypt_error}")
                raise ValueError(
                    "No se pudo desencriptar la contraseña de e.firma. "
                    "Por favor, vuelve a subir tus archivos y contraseña en la sección de Credenciales."
                )
            
            # Initialize e.firma service
            efirma_service = EfirmaService(
                cer_path=self.credentials.efirma_cer_path,
                key_path=self.credentials.efirma_key_path,
                password=efirma_password
            )
            
            # Verify certificate is valid
            is_valid, error_msg = efirma_service.is_valid()
            if not is_valid:
                raise ValueError(f"e.firma certificate invalid: {error_msg}")
            
            logger.info(f"e.firma loaded successfully - RFC: {efirma_service.get_rfc()}")
            
            # Initialize Web Service client
            ws_client = SATWebServiceClient(efirma_service)
            
            # Calculate date range (using date objects, not datetime)
            end_date = date.today()
            start_date = end_date - timedelta(days=months_back * 30)
            
            logger.info(f"Requesting CFDIs from {start_date} to {end_date}")
            
            # Download CFDIs emitidos (issued by user)
            logger.info("📥 Downloading CFDIs emitidos...")
            paquetes_emitidos = await ws_client.descarga_completa(
                fecha_inicio=start_date,
                fecha_fin=end_date,
                tipo_descarga=TipoDescarga.EMITIDOS,
                max_wait_minutes=30,
                poll_interval_seconds=30
            )
            
            results['cfdis_downloaded'] += len(paquetes_emitidos)
            logger.info(f"✅ Downloaded {len(paquetes_emitidos)} packages of CFDIs emitidos")
            
            # Download CFDIs recibidos (received by user)
            logger.info("📥 Downloading CFDIs recibidos...")
            paquetes_recibidos = await ws_client.descarga_completa(
                fecha_inicio=start_date,
                fecha_fin=end_date,
                tipo_descarga=TipoDescarga.RECIBIDOS,
                max_wait_minutes=30,
                poll_interval_seconds=30
            )
            
            results['cfdis_downloaded'] += len(paquetes_recibidos)
            logger.info(f"✅ Downloaded {len(paquetes_recibidos)} packages of CFDIs recibidos")
            
            # Process all packages
            all_paquetes = [
                (paq, 'emitido') for paq in paquetes_emitidos
            ] + [
                (paq, 'recibido') for paq in paquetes_recibidos
            ]
            
            for paquete_bytes, tipo in all_paquetes:
                try:
                    # Process package
                    logger.info(f"Processing {tipo} package...")
                    cfdis_data = PaqueteProcessor.process_paquete(paquete_bytes)
                    
                    for cfdi_data in cfdis_data:
                        try:
                            # Check for parsing errors
                            if 'error' in cfdi_data:
                                results['errors'].append({
                                    'tipo': tipo,
                                    'error': f"Parse error: {cfdi_data['error']}"
                                })
                                continue
                            
                            # Check if already exists
                            uuid = cfdi_data.get('uuid')
                            if uuid:
                                existing = self.db.query(CFDI).filter(
                                    CFDI.uuid == uuid,
                                    CFDI.user_id == self.user_id
                                ).first()
                                
                                if existing:
                                    results['cfdis_skipped'] += 1
                                    continue
                            
                            # Create CFDI record
                            cfdi = self._create_cfdi_from_parsed_data(cfdi_data)
                            self.db.add(cfdi)
                            self.db.commit()
                            
                            results['cfdis_processed'] += 1
                            
                            # Track totals
                            if cfdi.es_ingreso:
                                results['cfdis_emitidos'] += 1
                                results['total_ingresos'] += float(cfdi.total)
                            elif cfdi.es_egreso:
                                results['cfdis_recibidos'] += 1
                                results['total_egresos'] += float(cfdi.total)
                            
                            logger.debug(f"Processed CFDI: {uuid}")
                            
                        except Exception as e:
                            logger.error(f"Error processing CFDI: {str(e)}")
                            results['errors'].append({
                                'tipo': tipo,
                                'uuid': cfdi_data.get('uuid', 'unknown'),
                                'error': str(e)
                            })
                            continue
                    
                except Exception as e:
                    logger.error(f"Error processing {tipo} package: {str(e)}")
                    results['errors'].append({
                        'tipo': tipo,
                        'error': f"Package processing error: {str(e)}"
                    })
                    continue
                
            # Mark as completed
            results['status'] = SyncStatus.COMPLETED
            results['completed_at'] = datetime.utcnow().isoformat()
            
            # Update sync record
            sync_record.status = SyncStatus.COMPLETED
            sync_record.completed_at = datetime.utcnow()
            sync_record.duration_seconds = int((sync_record.completed_at - sync_record.started_at).total_seconds())
            sync_record.results = results
            self.db.commit()
            
            logger.info(f"Sync completed: {results['cfdis_processed']} CFDIs processed")
            
        except ValueError as e:
            # Configuration errors (missing e.firma, etc.)
            error_msg = str(e) if str(e) else "Configuration error (no details provided)"
            logger.error(f"Configuration error: {error_msg}", exc_info=True)
            results['status'] = SyncStatus.FAILED
            results['error'] = error_msg
            
            sync_record.status = SyncStatus.FAILED
            sync_record.completed_at = datetime.utcnow()
            sync_record.error_message = error_msg
            self.db.commit()
            
        except Exception as e:
            error_msg = str(e) if str(e) else f"Unexpected error: {type(e).__name__}"
            logger.error(f"Sync error: {error_msg}", exc_info=True)
            results['status'] = SyncStatus.FAILED
            results['error'] = error_msg
            
            sync_record.status = SyncStatus.FAILED
            sync_record.completed_at = datetime.utcnow()
            sync_record.error_message = error_msg
            self.db.commit()
            
        return results
        
    def _create_cfdi_from_parsed_data(self, cfdi_data: Dict) -> CFDI:
        """Create CFDI model from parsed package data (PaqueteProcessor output)"""
        from app.models import TipoComprobante, CFDIStatus
        from decimal import Decimal
        
        # Extract tax details
        impuestos = cfdi_data.get('impuestos', {})
        iva = Decimal('0')
        isr = Decimal('0')
        
        for traslado in impuestos.get('traslados', []):
            if traslado.get('impuesto') == '002':  # IVA
                iva += Decimal(str(traslado.get('importe', 0)))
        
        for retencion in impuestos.get('retenciones', []):
            if retencion.get('impuesto') == '001':  # ISR
                isr += Decimal(str(retencion.get('importe', 0)))
        
        # Determine tipo comprobante
        tipo_comp = cfdi_data.get('tipo_comprobante', 'I')
        
        # Create CFDI record
        cfdi = CFDI(
            user_id=self.user_id,
            uuid=cfdi_data.get('uuid'),
            serie=cfdi_data.get('serie'),
            folio=cfdi_data.get('folio'),
            version=cfdi_data.get('version'),
            tipo_comprobante=TipoComprobante(tipo_comp),
            fecha_emision=cfdi_data.get('fecha'),
            fecha_timbrado=cfdi_data.get('fecha_timbrado'),
            emisor_rfc=cfdi_data.get('emisor', {}).get('rfc'),
            emisor_nombre=cfdi_data.get('emisor', {}).get('nombre'),
            emisor_regimen_fiscal=cfdi_data.get('emisor', {}).get('regimen_fiscal'),
            receptor_rfc=cfdi_data.get('receptor', {}).get('rfc'),
            receptor_nombre=cfdi_data.get('receptor', {}).get('nombre'),
            receptor_uso_cfdi=cfdi_data.get('receptor', {}).get('uso_cfdi'),
            receptor_domicilio_fiscal=cfdi_data.get('receptor', {}).get('domicilio_fiscal'),
            receptor_regimen_fiscal=cfdi_data.get('receptor', {}).get('regimen_fiscal'),
            moneda=cfdi_data.get('moneda', 'MXN'),
            tipo_cambio=Decimal(str(cfdi_data.get('tipo_cambio', 1))),
            subtotal=Decimal(str(cfdi_data.get('subtotal', 0))),
            descuento=Decimal(str(cfdi_data.get('descuento', 0))),
            total=Decimal(str(cfdi_data.get('total', 0))),
            total_impuestos_trasladados=Decimal(str(impuestos.get('total_traslados', 0))),
            total_impuestos_retenidos=Decimal(str(impuestos.get('total_retenciones', 0))),
            iva_trasladado=iva,
            isr_retenido=isr,
            metodo_pago=cfdi_data.get('metodo_pago'),
            forma_pago=cfdi_data.get('forma_pago'),
            es_ingreso=(tipo_comp == 'I'),
            es_egreso=(tipo_comp == 'E'),
            es_nomina=(tipo_comp == 'N'),
            es_deducible=self._is_deducible_from_parsed(cfdi_data),
            status=CFDIStatus.VIGENTE,
            conceptos=cfdi_data.get('conceptos'),
            impuestos_detalle=impuestos,
            xml_content=cfdi_data.get('xml_content')  # Full XML stored in field
        )
        
        return cfdi
    
    def _is_deducible_from_parsed(self, cfdi_data: Dict) -> bool:
        """Check if CFDI is tax deductible from parsed data"""
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
        # Get most recent sync
        last_sync = self.db.query(SyncHistory).filter(
            SyncHistory.user_id == self.user_id
        ).order_by(SyncHistory.started_at.desc()).first()
        
        if last_sync:
            result = {
                'sync_id': last_sync.id,
                'status': last_sync.status.value,
                'sync_type': last_sync.sync_type.value,
                'started_at': last_sync.started_at.isoformat(),
                'completed_at': last_sync.completed_at.isoformat() if last_sync.completed_at else None,
                'duration_seconds': last_sync.duration_seconds,
                'results': last_sync.results or {},
                'error_message': last_sync.error_message
            }
            
            # Add current DB totals
            result['total_cfdis_db'] = self.db.query(CFDI).filter(
                CFDI.user_id == self.user_id
            ).count()
            
            return result
            
        return None
