"""
CFDI XML Parser
Parse Mexican CFDI (Comprobante Fiscal Digital por Internet) XML files
"""
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import xml.etree.ElementTree as ET
from pathlib import Path


class CFDIParser:
    """Parser for CFDI XML files (version 3.3 and 4.0)"""
    
    # Namespaces for CFDI versions
    NS_33 = {
        'cfdi': 'http://www.sat.gob.mx/cfd/3',
        'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
    }
    
    NS_40 = {
        'cfdi': 'http://www.sat.gob.mx/cfd/4',
        'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
    }
    
    def __init__(self, xml_path: str = None, xml_content: str = None):
        """Initialize parser with file path or XML content"""
        if xml_path:
            self.tree = ET.parse(xml_path)
        elif xml_content:
            self.tree = ET.ElementTree(ET.fromstring(xml_content))
        else:
            raise ValueError("Either xml_path or xml_content must be provided")
        
        self.root = self.tree.getroot()
        
        # Detect version and set namespace
        if 'http://www.sat.gob.mx/cfd/4' in self.root.tag:
            self.ns = self.NS_40
            self.version = '4.0'
        else:
            self.ns = self.NS_33
            self.version = '3.3'
    
    def parse(self) -> Dict:
        """Parse complete CFDI and return structured data"""
        return {
            'version': self.version,
            'serie': self.root.get('Serie'),
            'folio': self.root.get('Folio'),
            'fecha': self._parse_date(self.root.get('Fecha')),
            'tipo_comprobante': self.root.get('TipoDeComprobante'),
            'forma_pago': self.root.get('FormaPago'),
            'metodo_pago': self.root.get('MetodoPago'),
            'moneda': self.root.get('Moneda', 'MXN'),
            'tipo_cambio': self._parse_decimal(self.root.get('TipoCambio')),
            'subtotal': self._parse_decimal(self.root.get('SubTotal')),
            'descuento': self._parse_decimal(self.root.get('Descuento')),
            'total': self._parse_decimal(self.root.get('Total')),
            'emisor': self._parse_emisor(),
            'receptor': self._parse_receptor(),
            'conceptos': self._parse_conceptos(),
            'impuestos': self._parse_impuestos(),
            'timbre': self._parse_timbre(),
            'uuid': self._get_uuid()
        }
    
    def _parse_emisor(self) -> Dict:
        """Parse emisor (issuer) data"""
        emisor = self.root.find('cfdi:Emisor', self.ns)
        if emisor is None:
            return {}
        
        return {
            'rfc': emisor.get('Rfc'),
            'nombre': emisor.get('Nombre'),
            'regimen_fiscal': emisor.get('RegimenFiscal')
        }
    
    def _parse_receptor(self) -> Dict:
        """Parse receptor (receiver) data"""
        receptor = self.root.find('cfdi:Receptor', self.ns)
        if receptor is None:
            return {}
        
        return {
            'rfc': receptor.get('Rfc'),
            'nombre': receptor.get('Nombre'),
            'domicilio_fiscal': receptor.get('DomicilioFiscalReceptor'),
            'regimen_fiscal': receptor.get('RegimenFiscalReceptor'),
            'uso_cfdi': receptor.get('UsoCFDI')
        }
    
    def _parse_conceptos(self) -> List[Dict]:
        """Parse conceptos (line items)"""
        conceptos = []
        conceptos_node = self.root.find('cfdi:Conceptos', self.ns)
        
        if conceptos_node is None:
            return conceptos
        
        for concepto in conceptos_node.findall('cfdi:Concepto', self.ns):
            conceptos.append({
                'clave_prod_serv': concepto.get('ClaveProdServ'),
                'no_identificacion': concepto.get('NoIdentificacion'),
                'cantidad': self._parse_decimal(concepto.get('Cantidad')),
                'clave_unidad': concepto.get('ClaveUnidad'),
                'unidad': concepto.get('Unidad'),
                'descripcion': concepto.get('Descripcion'),
                'valor_unitario': self._parse_decimal(concepto.get('ValorUnitario')),
                'importe': self._parse_decimal(concepto.get('Importe')),
                'descuento': self._parse_decimal(concepto.get('Descuento')),
                'objeto_imp': concepto.get('ObjetoImp')
            })
        
        return conceptos
    
    def _parse_impuestos(self) -> Dict:
        """Parse impuestos (taxes)"""
        impuestos = self.root.find('cfdi:Impuestos', self.ns)
        
        if impuestos is None:
            return {
                'total_impuestos_trasladados': Decimal('0'),
                'total_impuestos_retenidos': Decimal('0'),
                'traslados': [],
                'retenciones': []
            }
        
        result = {
            'total_impuestos_trasladados': self._parse_decimal(
                impuestos.get('TotalImpuestosTrasladados')
            ),
            'total_impuestos_retenidos': self._parse_decimal(
                impuestos.get('TotalImpuestosRetenidos')
            ),
            'traslados': [],
            'retenciones': []
        }
        
        # Parse traslados (transferred taxes)
        traslados = impuestos.find('cfdi:Traslados', self.ns)
        if traslados is not None:
            for traslado in traslados.findall('cfdi:Traslado', self.ns):
                result['traslados'].append({
                    'impuesto': traslado.get('Impuesto'),
                    'tipo_factor': traslado.get('TipoFactor'),
                    'tasa_o_cuota': self._parse_decimal(traslado.get('TasaOCuota')),
                    'importe': self._parse_decimal(traslado.get('Importe')),
                    'base': self._parse_decimal(traslado.get('Base'))
                })
        
        # Parse retenciones (withheld taxes)
        retenciones = impuestos.find('cfdi:Retenciones', self.ns)
        if retenciones is not None:
            for retencion in retenciones.findall('cfdi:Retencion', self.ns):
                result['retenciones'].append({
                    'impuesto': retencion.get('Impuesto'),
                    'importe': self._parse_decimal(retencion.get('Importe'))
                })
        
        return result
    
    def _parse_timbre(self) -> Optional[Dict]:
        """Parse timbre fiscal digital (digital stamp)"""
        complemento = self.root.find('cfdi:Complemento', self.ns)
        if complemento is None:
            return None
        
        timbre = complemento.find('tfd:TimbreFiscalDigital', self.ns)
        if timbre is None:
            return None
        
        return {
            'uuid': timbre.get('UUID'),
            'fecha_timbrado': self._parse_date(timbre.get('FechaTimbrado')),
            'rfc_prov_certif': timbre.get('RfcProvCertif'),
            'sello_cfd': timbre.get('SelloCFD'),
            'no_certificado_sat': timbre.get('NoCertificadoSAT'),
            'sello_sat': timbre.get('SelloSAT'),
            'version': timbre.get('Version')
        }
    
    def _get_uuid(self) -> Optional[str]:
        """Get UUID from timbre"""
        timbre = self._parse_timbre()
        return timbre['uuid'] if timbre else None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO date string to datetime"""
        if not date_str:
            return None
        
        try:
            # Handle both with and without timezone
            if 'T' in date_str:
                if '+' in date_str or date_str.endswith('Z'):
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(date_str)
            else:
                return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return None
    
    def _parse_decimal(self, value: Optional[str]) -> Decimal:
        """Parse decimal value safely"""
        if not value:
            return Decimal('0')
        
        try:
            return Decimal(value)
        except Exception:
            return Decimal('0')
    
    def is_ingreso(self) -> bool:
        """Check if CFDI is an income document"""
        return self.root.get('TipoDeComprobante') == 'I'
    
    def is_egreso(self) -> bool:
        """Check if CFDI is an expense/refund document"""
        return self.root.get('TipoDeComprobante') == 'E'
    
    def is_nomina(self) -> bool:
        """Check if CFDI is a payroll document"""
        return self.root.get('TipoDeComprobante') == 'N'
    
    def is_deducible(self) -> bool:
        """
        Check if CFDI is potentially deductible
        Based on common deductible categories
        """
        uso_cfdi = self._parse_receptor().get('uso_cfdi', '')
        
        # Common deductible uso_cfdi codes
        deducible_codes = {
            'D01',  # Honorarios médicos
            'D02',  # Gastos médicos por incapacidad
            'D03',  # Gastos funerales
            'D04',  # Donativos
            'D05',  # Intereses reales hipotecarios
            'D06',  # Aportaciones voluntarias al SAR
            'D07',  # Primas por seguros de gastos médicos
            'D08',  # Gastos de transportación escolar
            'D09',  # Depósitos en cuentas para el ahorro
            'D10',  # Pagos por servicios educativos
        }
        
        return uso_cfdi in deducible_codes


def parse_cfdi_file(file_path: str) -> Dict:
    """Convenience function to parse a CFDI file"""
    parser = CFDIParser(xml_path=file_path)
    return parser.parse()


def parse_cfdi_content(xml_content: str) -> Dict:
    """Convenience function to parse CFDI XML content"""
    parser = CFDIParser(xml_content=xml_content)
    return parser.parse()
