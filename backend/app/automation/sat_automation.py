"""
SAT Automation - Web Scraping and Browser Automation
Automatiza la descarga de CFDIs desde el portal del SAT
"""
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path

import aiohttp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from app.core.config import settings

logger = logging.getLogger(__name__)

# SAT Portal URLs
SAT_PORTAL_URL = "https://www.sat.gob.mx"
SAT_LOGIN_URL = f"{SAT_PORTAL_URL}/usuarios/portal/portal.html"
SAT_CFDI_DESCARGA_URL = f"{SAT_PORTAL_URL}/aplicacion/descargamasiva/form.html"


class SATAutomation:
    """SAT Portal automation using Selenium"""
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.rfc: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self._cfdi_cache: Dict[str, List[Dict]] = {}
    
    def _init_driver(self):
        """Initialize Selenium Chrome driver"""
        if self.driver:
            return
        
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--start-maximized')
        
        # Headless mode for production
        if settings.get('HEADLESS_BROWSER', True):
            chrome_options.add_argument('--headless=new')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
    
    def _close_driver(self):
        """Close Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None
    
    async def login_sat(self, rfc: str, password: str) -> Dict[str, Any]:
        """
        Login to SAT portal
        
        Args:
            rfc: RFC sin homoclave (13 caracteres)
            password: Contraseña SAT
        
        Returns: {success: bool, message: str, session_data: dict}
        """
        try:
            self._init_driver()
            self.rfc = rfc
            
            logger.info(f"Attempting SAT login for RFC: {rfc}")
            
            # Navigate to login page
            self.driver.get(SAT_LOGIN_URL)
            
            # Wait for and fill RFC field
            wait = WebDriverWait(self.driver, 10)
            rfc_input = wait.until(EC.presence_of_element_located((By.NAME, "rfc")))
            rfc_input.clear()
            rfc_input.send_keys(rfc)
            
            # Fill password
            password_input = self.driver.find_element(By.NAME, "password")
            password_input.clear()
            password_input.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for navigation - check for dashboard or error
            wait.until(EC.url_changes(SAT_LOGIN_URL))
            await asyncio.sleep(2)  # Additional wait for page load
            
            current_url = self.driver.current_url
            
            # Check if login was successful
            if 'error' in current_url.lower() or 'login' in current_url.lower():
                logger.warning(f"Login failed for RFC {rfc}: URL is {current_url}")
                return {
                    "success": False,
                    "message": "Credenciales inválidas o fallo en login",
                    "session_data": None
                }
            
            # Get cookies for session persistence
            cookies = self.driver.get_cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            
            logger.info(f"SAT login successful for RFC: {rfc}")
            
            return {
                "success": True,
                "message": "Login exitoso en SAT",
                "session_data": {
                    "cookies": cookie_dict,
                    "url": current_url,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except TimeoutException:
            logger.error(f"Timeout during SAT login for RFC {rfc}")
            return {
                "success": False,
                "message": "Tiempo de espera agotado en login",
                "session_data": None
            }
        except Exception as e:
            logger.error(f"Login error for RFC {rfc}: {str(e)}")
            return {
                "success": False,
                "message": f"Error en login: {str(e)}",
                "session_data": None
            }
    
    async def get_cfdis(
        self,
        rfc: str,
        password: str,
        start_date: datetime,
        end_date: datetime,
        cfdi_type: str = "recibidos",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Download/Extract CFDI information from SAT portal
        
        Args:
            rfc: RFC del usuario
            password: Contraseña SAT
            start_date: Fecha inicio
            end_date: Fecha fin
            cfdi_type: "emitidos" o "recibidos"
            limit: Máximo de CFDIs a obtener
        
        Returns: {success: bool, data: List[Dict], message: str}
        """
        try:
            # Check cache first
            cache_key = f"{rfc}_{cfdi_type}_{start_date.date()}_{end_date.date()}"
            if cache_key in self._cfdi_cache:
                logger.info(f"Returning cached CFDIs for {cache_key}")
                return {
                    "success": True,
                    "data": self._cfdi_cache[cache_key],
                    "message": "CFDIs obtenidos del cache"
                }
            
            # Login first
            login_result = await self.login_sat(rfc, password)
            if not login_result["success"]:
                return {
                    "success": False,
                    "data": [],
                    "message": login_result["message"]
                }
            
            logger.info(f"Fetching {cfdi_type} CFDIs from {start_date} to {end_date}")
            
            # Navigate to descarga masiva
            self.driver.get(SAT_CFDI_DESCARGA_URL)
            wait = WebDriverWait(self.driver, 10)
            
            # Select CFDI type
            await asyncio.sleep(1)
            try:
                type_button = self.driver.find_element(
                    By.XPATH,
                    f"//input[@value='{cfdi_type}']"
                )
                type_button.click()
                await asyncio.sleep(1)
            except NoSuchElementException:
                logger.warning(f"Could not find CFDI type selector for {cfdi_type}")
            
            # Fill date range
            date_format = "%d/%m/%Y"
            start_str = start_date.strftime(date_format)
            end_str = end_date.strftime(date_format)
            
            try:
                fecha_inicio = self.driver.find_element(By.NAME, "fechaInicio")
                fecha_inicio.clear()
                fecha_inicio.send_keys(start_str)
                
                fecha_fin = self.driver.find_element(By.NAME, "fechaFin")
                fecha_fin.clear()
                fecha_fin.send_keys(end_str)
            except Exception as e:
                logger.error(f"Error filling date fields: {e}")
            
            # Click search button
            try:
                search_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Buscar')]"))
                )
                search_button.click()
                await asyncio.sleep(3)  # Wait for results to load
            except Exception as e:
                logger.error(f"Error clicking search button: {e}")
            
            # Extract CFDI data from table
            cfdis = await self._extract_cfdi_table(limit)
            
            # Cache results
            self._cfdi_cache[cache_key] = cfdis
            
            logger.info(f"Successfully extracted {len(cfdis)} CFDIs")
            
            return {
                "success": True,
                "data": cfdis,
                "message": f"Se obtuvieron {len(cfdis)} CFDIs"
            }
            
        except Exception as e:
            logger.error(f"Error getting CFDIs: {str(e)}")
            return {
                "success": False,
                "data": [],
                "message": f"Error al obtener CFDIs: {str(e)}"
            }
        finally:
            self._close_driver()
    
    async def _extract_cfdi_table(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Extract CFDI data from SAT table"""
        cfdis = []
        try:
            # Wait for table to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.XPATH, "//table//tr[@data-uuid]")))
            
            # Get all rows
            rows = self.driver.find_elements(By.XPATH, "//table//tr[@data-uuid]")
            
            for row in rows[:limit]:
                try:
                    # Extract data from row
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) >= 7:
                        cfdi_data = {
                            "uuid": row.get_attribute("data-uuid"),
                            "tipo": row.get_attribute("data-tipo") or "ingreso",
                            "fecha": self._parse_date(cells[1].text),
                            "rfc_emisor": cells[2].text.strip(),
                            "nombre_emisor": cells[3].text.strip(),
                            "rfc_receptor": cells[4].text.strip(),
                            "nombre_receptor": cells[5].text.strip(),
                            "total": self._parse_amount(cells[6].text),
                            "subtotal": self._parse_amount(cells[6].text) / 1.16,  # Aproximado
                            "status": row.get_attribute("data-status") or "vigente",
                            "moneda": "MXN",
                            "xml_url": f"/api/v1/cfdi/{row.get_attribute('data-uuid')}/xml",
                            "pdf_url": f"/api/v1/cfdi/{row.get_attribute('data-uuid')}/pdf"
                        }
                        cfdis.append(cfdi_data)
                except Exception as e:
                    logger.warning(f"Error extracting CFDI row: {e}")
                    continue
            
            logger.info(f"Extracted {len(cfdis)} CFDIs from table")
            
        except TimeoutException:
            logger.warning("Timeout waiting for CFDI table to load")
        except Exception as e:
            logger.error(f"Error extracting CFDI table: {e}")
        
        return cfdis
    
    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse date string from SAT"""
        try:
            # Try common formats
            for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            logger.warning(f"Could not parse date: {date_str}")
            return datetime.now()
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            return datetime.now()
    
    @staticmethod
    def _parse_amount(amount_str: str) -> float:
        """Parse amount string from SAT"""
        try:
            # Remove currency symbols and whitespace
            cleaned = amount_str.replace("$", "").replace(",", "").strip()
            return float(cleaned)
        except Exception as e:
            logger.warning(f"Error parsing amount {amount_str}: {e}")
            return 0.0
    
    def __enter__(self):
        """Context manager entry"""
        self._init_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self._close_driver()


# Helper function for quick use
async def validate_sat_credentials(rfc: str, password: str) -> bool:
    """Validate SAT credentials"""
    automation = SATAutomation()
    try:
        result = await automation.login_sat(rfc, password)
        return result["success"]
    finally:
        automation._close_driver()


async def fetch_cfdis_from_sat(
    rfc: str,
    password: str,
    start_date: datetime,
    end_date: datetime
) -> List[Dict[str, Any]]:
    """Fetch CFDIs from SAT portal"""
    automation = SATAutomation()
    try:
        result = await automation.get_cfdis(rfc, password, start_date, end_date)
        return result.get("data", [])
    finally:
        automation._close_driver()
