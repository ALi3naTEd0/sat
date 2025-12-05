"""
Cliente para Web Services del SAT - Descarga masiva de CFDIs.

El SAT proporciona 3 web services SOAP para descarga masiva:
1. SolicitaDescarga: Crear solicitud de descarga
2. VerificaSolicitud: Verificar estado de la solicitud
3. DescargaMasiva: Descargar el paquete cuando esté listo

Documentación oficial:
https://www.sat.gob.mx/consultas/42968/consulta-y-recuperacion-de-comprobantes-(factura-electronica)
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import base64
import asyncio
import logging

from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session

from .efirma_service import EfirmaService

logger = logging.getLogger(__name__)


class TipoSolicitud(str, Enum):
    """Tipos de solicitud según el SAT."""
    CFDI = "CFDI"  # Solicitud de CFDIs


class TipoDescarga(str, Enum):
    """Tipo de descarga según emisor/receptor."""
    EMITIDOS = "emitidos"
    RECIBIDOS = "recibidos"


class EstadoSolicitud(str, Enum):
    """Estados posibles de una solicitud de descarga."""
    ACEPTADA = "1"  # Solicitud aceptada
    EN_PROCESO = "2"  # En proceso
    TERMINADA = "3"  # Terminada, paquetes listos
    ERROR = "4"  # Error en la solicitud
    RECHAZADA = "5"  # Solicitud rechazada
    VENCIDA = "6"  # Solicitud vencida


# URLs de Web Services del SAT (Ambiente de producción)
WSDL_SOLICITA_DESCARGA = "https://cfdidescargamasiva.clouda.sat.gob.mx/SolicitaDescargaService.svc?wsdl"
WSDL_VERIFICA_SOLICITUD = "https://cfdidescargamasiva.clouda.sat.gob.mx/VerificaSolicitudDescargaService.svc?wsdl"
WSDL_DESCARGA_MASIVA = "https://cfdidescargamasiva.clouda.sat.gob.mx/DescargaMasivaTercerosService.svc?wsdl"


class SATWebServiceClient:
    """Cliente para interactuar con los Web Services del SAT."""
    
    def __init__(self, efirma_service: EfirmaService):
        """
        Inicializar cliente de Web Services.
        
        Args:
            efirma_service: Servicio de e.firma configurado
        
        Raises:
            ConnectionError: Si no se puede conectar a los servicios del SAT
        """
        self.efirma = efirma_service
        
        try:
            # Configurar transporte HTTP con timeout
            session = Session()
            session.verify = True
            transport = Transport(session=session, timeout=30)
            
            # Configurar zeep con opciones
            settings = Settings(strict=False, xml_huge_tree=True)
            
            # Inicializar clientes SOAP
            self.client_solicita = Client(WSDL_SOLICITA_DESCARGA, settings=settings, transport=transport)
            self.client_verifica = Client(WSDL_VERIFICA_SOLICITUD, settings=settings, transport=transport)
            self.client_descarga = Client(WSDL_DESCARGA_MASIVA, settings=settings, transport=transport)
        except Exception as e:
            raise ConnectionError(
                f"No se pudo conectar a los Web Services del SAT. "
                f"Verifica tu conexión a internet. Error: {str(e)}"
            )
    
    def _create_auth_header(self) -> Dict[str, Any]:
        """
        Crear encabezado de autenticación con e.firma.
        
        Returns:
            Diccionario con datos de autenticación
        """
        return {
            'RfcSolicitante': self.efirma.get_rfc(),
            'NoCertificado': self.efirma.get_certificate_serial(),
            'Certificado': self.efirma.get_certificate_base64()
        }
    
    async def solicita_descarga(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime,
        tipo_descarga: TipoDescarga,
        rfc_emisor: Optional[str] = None,
        rfc_receptor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Solicitar descarga masiva de CFDIs.
        
        Args:
            fecha_inicio: Fecha inicial del periodo
            fecha_fin: Fecha final del periodo
            tipo_descarga: Si buscar CFDIs emitidos o recibidos
            rfc_emisor: RFC del emisor (opcional, para filtrar)
            rfc_receptor: RFC del receptor (opcional, para filtrar)
            
        Returns:
            Diccionario con IdSolicitud, CodEstatus, Mensaje
        """
        try:
            # Preparar parámetros según tipo de descarga
            rfc_solicitante = self.efirma.get_rfc()
            
            # Si busca emitidos, el RFC solicitante es el emisor
            if tipo_descarga == TipoDescarga.EMITIDOS:
                rfc_emisor = rfc_solicitante
            # Si busca recibidos, el RFC solicitante es el receptor
            else:
                rfc_receptor = rfc_solicitante
            
            # Crear solicitud
            solicitud = {
                'RfcEmisor': rfc_emisor or '',
                'RfcReceptor': rfc_receptor or '',
                'FechaInicial': fecha_inicio.strftime('%Y-%m-%dT%H:%M:%S'),
                'FechaFinal': fecha_fin.strftime('%Y-%m-%dT%H:%M:%S'),
                'TipoSolicitud': TipoSolicitud.CFDI.value
            }
            
            # Crear cadena original para firmar
            cadena_original = (
                f"{solicitud['RfcEmisor']}|"
                f"{solicitud['RfcReceptor']}|"
                f"{solicitud['FechaInicial']}|"
                f"{solicitud['FechaFinal']}|"
                f"{solicitud['TipoSolicitud']}"
            )
            
            # Firmar solicitud
            firma = self.efirma.sign_string(cadena_original)
            
            # Llamar web service
            resultado = await asyncio.to_thread(
                self.client_solicita.service.SolicitaDescarga,
                solicitud=solicitud,
                firma=firma,
                **self._create_auth_header()
            )
            
            logger.info(f"Solicitud de descarga creada: {resultado}")
            
            return {
                'id_solicitud': resultado.IdSolicitud,
                'cod_estatus': resultado.CodEstatus,
                'mensaje': resultado.Mensaje
            }
            
        except Exception as e:
            logger.error(f"Error al solicitar descarga: {e}")
            raise
    
    async def verifica_solicitud(self, id_solicitud: str) -> Dict[str, Any]:
        """
        Verificar estado de una solicitud de descarga.
        
        Args:
            id_solicitud: ID de la solicitud a verificar
            
        Returns:
            Diccionario con EstadoSolicitud, CodigoEstadoSolicitud, NumeroArchivos, Mensaje
        """
        try:
            # Llamar web service
            resultado = await asyncio.to_thread(
                self.client_verifica.service.VerificaSolicitudDescarga,
                idSolicitud=id_solicitud,
                **self._create_auth_header()
            )
            
            logger.info(f"Estado de solicitud {id_solicitud}: {resultado}")
            
            # Extraer IDs de paquetes si están disponibles
            ids_paquetes = []
            if hasattr(resultado, 'IdsPaquetes') and resultado.IdsPaquetes:
                ids_paquetes = resultado.IdsPaquetes.split(',')
            
            return {
                'estado_solicitud': resultado.EstadoSolicitud,
                'codigo_estado': resultado.CodigoEstadoSolicitud,
                'numero_archivos': resultado.NumeroArchivos if hasattr(resultado, 'NumeroArchivos') else 0,
                'ids_paquetes': ids_paquetes,
                'mensaje': resultado.Mensaje
            }
            
        except Exception as e:
            logger.error(f"Error al verificar solicitud {id_solicitud}: {e}")
            raise
    
    async def descarga_paquete(self, id_paquete: str) -> bytes:
        """
        Descargar un paquete de CFDIs.
        
        Args:
            id_paquete: ID del paquete a descargar
            
        Returns:
            Contenido del paquete en bytes (archivo ZIP)
        """
        try:
            # Llamar web service
            resultado = await asyncio.to_thread(
                self.client_descarga.service.DescargaMasivaTerceros,
                idPaquete=id_paquete,
                **self._create_auth_header()
            )
            
            logger.info(f"Paquete {id_paquete} descargado exitosamente")
            
            # El paquete viene en Base64
            if hasattr(resultado, 'Paquete'):
                return base64.b64decode(resultado.Paquete)
            else:
                raise ValueError(f"Respuesta no contiene paquete: {resultado}")
            
        except Exception as e:
            logger.error(f"Error al descargar paquete {id_paquete}: {e}")
            raise
    
    async def descarga_completa(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime,
        tipo_descarga: TipoDescarga,
        max_wait_minutes: int = 30,
        poll_interval_seconds: int = 30
    ) -> List[bytes]:
        """
        Flujo completo: solicitar → esperar → verificar → descargar.
        
        Args:
            fecha_inicio: Fecha inicial del periodo
            fecha_fin: Fecha final del periodo
            tipo_descarga: Si buscar CFDIs emitidos o recibidos
            max_wait_minutes: Máximo tiempo de espera en minutos
            poll_interval_seconds: Intervalo de verificación en segundos
            
        Returns:
            Lista de paquetes descargados (bytes de archivos ZIP)
        """
        # 1. Solicitar descarga
        resultado_solicitud = await self.solicita_descarga(
            fecha_inicio, fecha_fin, tipo_descarga
        )
        
        id_solicitud = resultado_solicitud['id_solicitud']
        logger.info(f"Solicitud creada: {id_solicitud}")
        
        # 2. Esperar y verificar estado
        max_iterations = (max_wait_minutes * 60) // poll_interval_seconds
        
        for i in range(max_iterations):
            await asyncio.sleep(poll_interval_seconds)
            
            estado = await self.verifica_solicitud(id_solicitud)
            codigo_estado = estado['codigo_estado']
            
            if codigo_estado == EstadoSolicitud.TERMINADA.value:
                logger.info(f"Solicitud {id_solicitud} terminada, {estado['numero_archivos']} paquetes disponibles")
                break
            elif codigo_estado in [EstadoSolicitud.ERROR.value, EstadoSolicitud.RECHAZADA.value]:
                raise ValueError(f"Solicitud fallida: {estado['mensaje']}")
            elif codigo_estado == EstadoSolicitud.VENCIDA.value:
                raise ValueError("Solicitud vencida")
            
            logger.info(f"Solicitud en proceso... ({i+1}/{max_iterations})")
        else:
            raise TimeoutError(f"Timeout esperando solicitud {id_solicitud}")
        
        # 3. Descargar paquetes
        ids_paquetes = estado['ids_paquetes']
        paquetes = []
        
        for id_paquete in ids_paquetes:
            logger.info(f"Descargando paquete {id_paquete}...")
            paquete_bytes = await self.descarga_paquete(id_paquete)
            paquetes.append(paquete_bytes)
        
        logger.info(f"Descarga completa: {len(paquetes)} paquetes descargados")
        return paquetes
