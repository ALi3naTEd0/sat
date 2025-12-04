"""
SAT Portal Scraper - Automated data collection from Portal SAT
Uses Playwright for web automation
"""
from playwright.async_api import async_playwright, Page, Browser
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import asyncio
import logging
import os
from pathlib import Path

# Configure logging at module level
logging.basicConfig(level=logging.INFO)


class SATScraperException(Exception):
    """Custom exception for SAT scraper errors"""
    pass


class SATScraper:
    """
    Scraper for Portal SAT (sat.gob.mx)
    Automates login and data extraction
    """
    
    BASE_URL = "https://www.sat.gob.mx"
    # Portal actualizado 2025 - CFDI sin e.firma
    CFDIS_URL = "https://portalcfdi.facturaelectronica.sat.gob.mx"
    # URL alternativa para login solo con CIEC (sin e.firma)
    LOGIN_CIEC_URL = "https://cfdiau.sat.gob.mx/nidp/app/login?id=SATx509Custom&sid=0&option=credential&sid=0"
    
    def __init__(self, rfc: str, password: str, headless: bool = True):
        """
        Initialize SAT scraper
        
        Args:
            rfc: RFC del contribuyente
            password: Contraseña del portal SAT
            headless: Run browser in headless mode
        """
        self.rfc = rfc.upper()
        self.password = password
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.session_cookies = None  # Store session cookies
        
    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
        
    async def start(self):
        """Start browser and create page"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        
        # Set reasonable timeout
        self.page.set_default_timeout(30000)  # 30 seconds
        
        logging.info("Browser started")
        
    async def close(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
            logging.info("Browser closed")
    
    def get_session_cookies(self) -> Optional[list]:
        """Get captured session cookies after successful login"""
        return self.session_cookies
    
    async def restore_session(self, cookies: list):
        """Restore a previous session using saved cookies"""
        if not self.page:
            await self.start()
        
        await self.page.context.add_cookies(cookies)
        logging.info(f"Restored {len(cookies)} cookies")
        self.is_logged_in = True
            
    async def login(self) -> bool:
        """
        Login to Portal SAT con CIEC (Contraseña de Acceso) - SIN e.firma
        
        Returns:
            True if login successful
        """
        try:
            logging.info(f"Logging in as {self.rfc} using CIEC (password only)")
            
            # Navigate directly to CIEC login (password-based, no e.firma)
            # Try the main CFDI portal first, it should redirect to appropriate login
            await self.page.goto(self.CFDIS_URL, wait_until="networkidle")
            
            # Tomar screenshot para debug
            try:
                await self.page.screenshot(path="/tmp/sat_login_1.png")
                logging.info("Screenshot saved: /tmp/sat_login_1.png")
            except:
                pass
            
            # Esperar a que cargue la página
            await asyncio.sleep(2)
            
            # IMPORTANTE: Buscar y hacer clic en la opción de login con CONTRASEÑA (sin e.firma)
            # El portal SAT puede tener opciones: "e.firma" vs "Contraseña"
            password_login_selectors = [
                'a:has-text("Contraseña")',
                'button:has-text("Contraseña")',
                'a:has-text("CIEC")',
                'button:has-text("CIEC")',
                'a[href*="password"]',
                'a[href*="ciec"]',
                '#passwordLogin',
                '.password-login'
            ]
            
            for selector in password_login_selectors:
                try:
                    password_option = await self.page.wait_for_selector(selector, timeout=2000)
                    if password_option:
                        logging.info(f"Found password login option: {selector}")
                        await password_option.click()
                        await asyncio.sleep(2)
                        logging.info("Clicked on password login option")
                        break
                except:
                    continue
            
            # Screenshot después de seleccionar método de login
            try:
                await self.page.screenshot(path="/tmp/sat_login_1b.png")
                logging.info("Screenshot saved: /tmp/sat_login_1b.png")
            except:
                pass
            
            # Buscar el campo de RFC (puede tener diferentes selectores)
            rfc_selectors = [
                'input[name="rfc"]',
                'input[id="rfc"]',
                'input[placeholder*="RFC"]',
                '#Ecom_User_ID',
                'input[type="text"]'
            ]
            
            rfc_input = None
            for selector in rfc_selectors:
                try:
                    rfc_input = await self.page.wait_for_selector(selector, timeout=3000)
                    if rfc_input:
                        logging.info(f"Found RFC input with selector: {selector}")
                        break
                except:
                    continue
            
            if not rfc_input:
                # Get page content for debugging
                content = await self.page.content()
                logging.error(f"Could not find RFC input. Page title: {await self.page.title()}")
                logging.error(f"Current URL: {self.page.url}")
                raise SATScraperException("No se encontró el campo de RFC en el formulario de login")
            
            # Fill RFC
            await rfc_input.fill(self.rfc)
            logging.info("RFC filled")
            
            # Buscar campo de contraseña
            password_selectors = [
                'input[name="password"]',
                'input[id="password"]',
                'input[type="password"]',
                '#Ecom_Password'
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = await self.page.wait_for_selector(selector, timeout=3000)
                    if password_input:
                        logging.info(f"Found password input with selector: {selector}")
                        break
                except:
                    continue
            
            if not password_input:
                raise SATScraperException("No se encontró el campo de contraseña")
            
            # Fill password
            await password_input.fill(self.password)
            logging.info("Password filled")
            
            # Screenshot antes de submit
            try:
                await self.page.screenshot(path="/tmp/sat_login_2.png")
                logging.info("Screenshot saved: /tmp/sat_login_2.png")
            except:
                pass
            
            # Buscar botón de submit
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Iniciar")',
                'button:has-text("Enviar")',
                'button:has-text("Ingresar")'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = await self.page.wait_for_selector(selector, timeout=2000)
                    if submit_btn:
                        logging.info(f"Found submit button with selector: {selector}")
                        await submit_btn.click()
                        break
                except:
                    continue
            
            # Esperar navegación
            await asyncio.sleep(3)
            
            # Screenshot después de submit
            try:
                await self.page.screenshot(path="/tmp/sat_login_3.png")
                logging.info("Screenshot saved: /tmp/sat_login_3.png")
            except:
                pass
            
            # Esperar y monitorear que el usuario complete login/CAPTCHA
            logging.info("Waiting for user to complete login (including CAPTCHA if present)...")
            logging.info("You have 60 seconds to log in manually in the browser window...")
            
            # Verificar periódicamente si ya se completó el login
            max_wait_time = 60  # segundos
            check_interval = 3  # verificar cada 3 segundos
            elapsed = 0
            
            while elapsed < max_wait_time:
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                
                current_url = self.page.url
                logging.info(f"[{elapsed}s] Current URL: {current_url}")
                
                # Si llegamos al portal de CFDI, fue exitoso
                if 'portalcfdi.facturaelectronica.sat.gob.mx' in current_url.lower():
                    self.is_logged_in = True
                    logging.info("✅ Login detected successful - Reached CFDI portal!")
                    
                    # CAPTURAR COOKIES DE SESIÓN
                    self.session_cookies = await self.page.context.cookies()
                    logging.info(f"Captured {len(self.session_cookies)} cookies")
                    
                    # Log important cookies (sin valores sensibles)
                    for cookie in self.session_cookies:
                        logging.info(f"Cookie: {cookie['name']} from {cookie['domain']}")
                    
                    return True
                
                # Si salimos de la página de login pero no llegamos al portal aún
                if 'nidp' not in current_url.lower() and 'wsfed' not in current_url.lower() and 'login' not in current_url.lower():
                    # Esperar un poco más por si está redirigiendo
                    logging.info("Left login page, waiting for final redirect...")
                    await asyncio.sleep(5)
                    
                    current_url = self.page.url
                    if 'portalcfdi' in current_url.lower() or 'sat.gob.mx' in current_url.lower():
                        self.is_logged_in = True
                        logging.info("✅ Login detected successful - URL changed to SAT domain")
                        
                        # CAPTURAR COOKIES DE SESIÓN
                        self.session_cookies = await self.page.context.cookies()
                        logging.info(f"Captured {len(self.session_cookies)} cookies")
                        
                        return True
            
            # Después de 60 segundos, verificar una última vez
            current_url = self.page.url
            logging.info(f"Final URL after {max_wait_time}s: {current_url}")
            # Después de 60 segundos, verificar una última vez
            current_url = self.page.url
            logging.info(f"Final URL after {max_wait_time}s: {current_url}")
            
            # Última verificación con selectores si no detectamos por URL
            if 'portalcfdi' in current_url.lower() or ('sat.gob.mx' in current_url.lower() and 'login' not in current_url.lower()):
                self.is_logged_in = True
                logging.info("✅ Login successful (final check)")
                self.session_cookies = await self.page.context.cookies()
                logging.info(f"Captured {len(self.session_cookies)} cookies")
                return True
            
            # Si seguimos en login, intentar detectar con selectores
            # Buscar indicadores de login exitoso
            success_selectors = [
                '.user-menu',
                '.dashboard',
                '#principal',
                'text=Bienvenido',
                'text=Mis Facturas',
                'text=Consulta',
                '[href*="logout"]',
                '[href*="salir"]'
            ]
            
            for selector in success_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        self.is_logged_in = True
                        logging.info(f"Login detected successful (selector: {selector})")
                        
                        # CAPTURAR COOKIES DE SESIÓN
                        self.session_cookies = await self.page.context.cookies()
                        logging.info(f"Captured {len(self.session_cookies)} cookies")
                        
                        await asyncio.sleep(2)
                        return True
                except:
                    continue
            
            # Si llegamos aquí, no detectamos login exitoso
            # Buscar mensajes de error
            error_msg = await self._get_error_message()
            if error_msg:
                logging.error(f"Login failed: {error_msg}")
                raise SATScraperException(error_msg)
            
            # No encontramos ni éxito ni error
            logging.warning("Could not determine login status")
            return False
                    
        except Exception as e:
            logging.error(f"Login error: {str(e)}")
            raise SATScraperException(f"Error during login: {str(e)}")
            
    async def _get_error_message(self) -> Optional[str]:
        """Extract error message from page"""
        try:
            # Try to get the full page text to capture any error
            page_text = await self.page.inner_text('body')
            
            # Common error patterns
            error_patterns = [
                'certificado debe ser Renovado',
                'contraseña incorrecta',
                'RFC no válido',
                'cuenta bloqueada',
                'servicio no disponible'
            ]
            
            for pattern in error_patterns:
                if pattern.lower() in page_text.lower():
                    # Find the surrounding text
                    start = max(0, page_text.lower().find(pattern.lower()) - 50)
                    end = min(len(page_text), page_text.lower().find(pattern.lower()) + len(pattern) + 150)
                    return page_text[start:end].strip()
            
            # Try specific selectors
            error_selectors = [
                '.error-message',
                '.alert-danger',
                '.mensaje-error',
                '[class*="error"]',
                '[class*="alert"]'
            ]
            
            for selector in error_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    text = await elements[0].inner_text()
                    if text and text.strip():
                        return text.strip()
                        
            return None
            
        except:
            return None
            
    async def download_cfdis(
        self, 
        start_date: date, 
        end_date: date,
        download_dir: str,
        tipo: str = "todos"  # "emitidos", "recibidos", "todos"
    ) -> List[Dict]:
        """
        Download CFDIs for date range
        
        Args:
            start_date: Start date
            end_date: End date
            download_dir: Directory to save XMLs
            tipo: Type of CFDIs (emitidos, recibidos, todos)
            
        Returns:
            List of downloaded CFDI metadata
        """
        if not self.is_logged_in:
            raise SATScraperException("Not logged in")
            
        logging.info(f"Downloading CFDIs from {start_date} to {end_date}")
        
        try:
            # Navigate to CFDI section
            await self.page.goto(f"{self.CFDIS_URL}/Consulta")
            
            # Wait for date filters
            await self.page.wait_for_selector('input[name="fechaInicio"]')
            
            # Fill date range
            await self.page.fill('input[name="fechaInicio"]', start_date.strftime('%d/%m/%Y'))
            await self.page.fill('input[name="fechaFin"]', end_date.strftime('%d/%m/%Y'))
            
            # Select type if filter exists
            if tipo != "todos":
                try:
                    await self.page.select_option('select[name="tipo"]', tipo)
                except:
                    pass  # Filter might not exist
            
            # Click search
            await self.page.click('button[type="submit"], input[value="Buscar"]')
            
            # Wait for results
            await self.page.wait_for_selector('.cfdi-list, .resultado, table', timeout=15000)
            
            # Get all CFDI links
            cfdi_links = await self.page.query_selector_all('a[href*="xml"], a[href*="descargar"]')
            
            downloaded = []
            os.makedirs(download_dir, exist_ok=True)
            
            for link in cfdi_links:
                try:
                    # Get UUID from link or metadata
                    uuid = await self._extract_uuid_from_link(link)
                    
                    # Download XML
                    async with self.page.expect_download() as download_info:
                        await link.click()
                        
                    download = await download_info.value
                    
                    # Save file
                    filename = f"{uuid}.xml" if uuid else download.suggested_filename
                    filepath = os.path.join(download_dir, filename)
                    await download.save_as(filepath)
                    
                    downloaded.append({
                        'uuid': uuid,
                        'filepath': filepath,
                        'filename': filename
                    })
                    
                    logging.info(f"Downloaded: {filename}")
                    
                except Exception as e:
                    logging.warning(f"Failed to download CFDI: {str(e)}")
                    continue
                    
            logging.info(f"Downloaded {len(downloaded)} CFDIs")
            return downloaded
            
        except Exception as e:
            logging.error(f"Error downloading CFDIs: {str(e)}")
            raise SATScraperException(f"Error downloading CFDIs: {str(e)}")
            
    async def _extract_uuid_from_link(self, link) -> Optional[str]:
        """Extract UUID from CFDI link"""
        try:
            # Try to get UUID from href
            href = await link.get_attribute('href')
            if href and 'uuid=' in href.lower():
                uuid = href.split('uuid=')[1].split('&')[0]
                return uuid
                
            # Try to get from data attributes
            uuid = await link.get_attribute('data-uuid')
            if uuid:
                return uuid
                
            # Try to get from parent row
            row = await link.evaluate_handle('element => element.closest("tr")')
            if row:
                cells = await row.query_selector_all('td')
                for cell in cells:
                    text = await cell.inner_text()
                    # UUID format: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                    if len(text) == 36 and text.count('-') == 4:
                        return text
                        
            return None
            
        except:
            return None
            
    async def get_constancia_fiscal(self, download_dir: str) -> Optional[str]:
        """
        Download Constancia de Situación Fiscal
        
        Args:
            download_dir: Directory to save PDF
            
        Returns:
            Path to downloaded file
        """
        if not self.is_logged_in:
            raise SATScraperException("Not logged in")
            
        logging.info("Downloading Constancia de Situación Fiscal")
        
        try:
            # Navigate to constancia section
            await self.page.goto(f"{self.BASE_URL}/tramites/31274/obten-tu-constancia-de-situacion-fiscal")
            
            # Look for download button
            await self.page.wait_for_selector('a[href*="constancia"], button:has-text("Descargar")', timeout=10000)
            
            # Click download
            async with self.page.expect_download() as download_info:
                await self.page.click('a[href*="constancia"], button:has-text("Descargar")')
                
            download = await download_info.value
            
            # Save file
            os.makedirs(download_dir, exist_ok=True)
            filename = f"constancia_fiscal_{datetime.now().strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(download_dir, filename)
            await download.save_as(filepath)
            
            logging.info(f"Constancia downloaded: {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"Error downloading constancia: {str(e)}")
            return None
            
    async def get_declaraciones(self, year: int) -> List[Dict]:
        """
        Get list of declarations for a year
        
        Args:
            year: Tax year
            
        Returns:
            List of declarations metadata
        """
        if not self.is_logged_in:
            raise SATScraperException("Not logged in")
            
        logging.info(f"Getting declarations for {year}")
        
        try:
            # Navigate to declarations section
            await self.page.goto(f"{self.BASE_URL}/declaraciones")
            
            # Wait for year selector
            await self.page.wait_for_selector('select[name="ejercicio"]')
            
            # Select year
            await self.page.select_option('select[name="ejercicio"]', str(year))
            
            # Wait for results
            await self.page.wait_for_selector('.declaracion-list, table')
            
            # Extract declarations
            rows = await self.page.query_selector_all('tr.declaracion, tbody tr')
            
            declaraciones = []
            for row in rows:
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) >= 3:
                        tipo = await cells[0].inner_text()
                        periodo = await cells[1].inner_text()
                        status = await cells[2].inner_text()
                        
                        declaraciones.append({
                            'tipo': tipo.strip(),
                            'periodo': periodo.strip(),
                            'status': status.strip(),
                            'year': year
                        })
                        
                except:
                    continue
                    
            logging.info(f"Found {len(declaraciones)} declarations")
            return declaraciones
            
        except Exception as e:
            logging.error(f"Error getting declarations: {str(e)}")
            return []


async def test_scraper():
    """Test scraper functionality"""
    # This is just for testing - in production use real credentials
    rfc = "XAXX010101000"
    password = "test123"
    
    async with SATScraper(rfc, password, headless=False) as scraper:
        # Try login
        await scraper.login()
        
        # Download last month CFDIs
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        cfdis = await scraper.download_cfdis(
            start_date=start_date,
            end_date=end_date,
            download_dir="/tmp/cfdis_test"
        )
        
        print(f"Downloaded {len(cfdis)} CFDIs")


if __name__ == "__main__":
    asyncio.run(test_scraper())
