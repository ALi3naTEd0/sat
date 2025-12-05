"""
Streamlit Frontend - Gestor Fiscal Personal
"""
import streamlit as st
import requests
import os
import json
from datetime import datetime
from typing import Optional

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

# Load session from query params (used for persistence)
def load_session():
    """Load session from query params or initialize"""
    query_params = st.query_params
    
    if "token" in query_params:
        token = query_params["token"]
        st.session_state.token = token
        
        # Get user info
        response = requests.get(
            f"{API_BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            st.session_state.user = response.json()
        else:
            # Token expired
            st.session_state.token = None
            st.query_params.clear()

def save_session():
    """Save session to query params"""
    if st.session_state.token:
        st.query_params["token"] = st.session_state.token

# Session state initialization
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "backend_status" not in st.session_state:
    st.session_state.backend_status = None
if "show_update_creds" not in st.session_state:
    st.session_state.show_update_creds = False

# Load session on startup
load_session()


def check_backend_health():
    """Check if backend is reachable"""
    try:
        response = requests.get(f"{API_BASE_URL.replace('/api/v1', '')}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def show_connection_status():
    """Display connection status indicator in bottom right corner"""
    is_connected = check_backend_health()
    st.session_state.backend_status = is_connected
    
    status_color = "#28a745" if is_connected else "#dc3545"
    status_text = "Conectado" if is_connected else "Desconectado"
    status_icon = "🟢" if is_connected else "🔴"
    
    st.markdown(
        f"""
        <div style="position: fixed; bottom: 20px; right: 20px; z-index: 999; 
                    background: white; border: 1px solid {status_color}; 
                    border-radius: 8px; padding: 6px 12px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    font-size: 12px;">
            <span style="margin-right: 4px;">{status_icon}</span>
            <span style="color: {status_color}; font-weight: 500;">{status_text}</span>
        </div>
        """,
        unsafe_allow_html=True
    )


def api_request(endpoint: str, method: str = "GET", data: dict = None, files: dict = None, form_data: bool = False, params: dict = None):
    """Make API request with authentication"""
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    
    url = f"{API_BASE_URL}{endpoint}"
    
    # Timeout más largo para validación de credenciales (scraping puede tardar)
    timeout = 120 if "/validate" in endpoint else 30
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
        elif method == "POST":
            if files:
                response = requests.post(url, headers=headers, data=data, files=files, params=params, timeout=timeout)
            elif form_data:
                response = requests.post(url, headers=headers, data=data, params=params, timeout=timeout)
            else:
                response = requests.post(url, headers=headers, json=data, params=params, timeout=timeout)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, params=params, timeout=timeout)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, params=params, timeout=timeout)
        
        return response
    except requests.exceptions.ConnectionError as e:
        st.error(f"⚠️ Error de conexión: {str(e)}\n\nURL: {url}")
        return None
    except requests.exceptions.Timeout as e:
        st.error(f"⚠️ Timeout: El servidor tardó demasiado en responder\n\nURL: {url}")
        return None
    except Exception as e:
        st.error(f"⚠️ Error inesperado: {type(e).__name__}: {str(e)}\n\nURL: {url}")
        return None


def login_page():
    """Login/Register page"""
    st.title("🏛️ Gestor Fiscal Personal SAT")
    
    tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
    
    with tab1:
        st.subheader("Iniciar Sesión")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Iniciar Sesión")
            
            if submit:
                response = api_request("/auth/login", "POST", {
                    "username": email,
                    "password": password
                }, form_data=True)
                
                if response and response.status_code == 200:
                    data = response.json()
                    st.session_state.token = data["access_token"]
                    
                    # Get user info
                    user_response = api_request("/auth/me")
                    if user_response and user_response.status_code == 200:
                        st.session_state.user = user_response.json()
                        save_session()  # Persist session
                        st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
    
    with tab2:
        st.subheader("Crear Cuenta")
        with st.form("register_form"):
            email = st.text_input("Email")
            phone = st.text_input("Teléfono (opcional)")
            password = st.text_input("Contraseña", type="password")
            password2 = st.text_input("Confirmar Contraseña", type="password")
            first_name = st.text_input("Nombre")
            last_name = st.text_input("Apellidos")
            submit = st.form_submit_button("Registrarse")
            
            if submit:
                if password != password2:
                    st.error("❌ Las contraseñas no coinciden")
                elif len(password) < 8:
                    st.error("❌ La contraseña debe tener al menos 8 caracteres")
                else:
                    response = api_request("/auth/register", "POST", {
                        "email": email,
                        "phone": phone if phone else None,
                        "password": password,
                        "first_name": first_name,
                        "last_name": last_name
                    })
                    
                    if response and response.status_code == 200:
                        st.success("✅ Cuenta creada exitosamente. Por favor inicia sesión.")
                    elif response:
                        error_data = response.json()
                        if isinstance(error_data.get("detail"), list):
                            # Validation errors (422)
                            errors = error_data["detail"]
                            error_msg = "\n".join([f"• {e.get('msg', str(e))}" for e in errors])
                            st.error(f"❌ Error de validación:\n{error_msg}")
                        elif isinstance(error_data.get("detail"), str):
                            # Simple error message (400, etc)
                            st.error(f"❌ {error_data['detail']}")
                        else:
                            st.error(f"❌ Error al crear cuenta (código {response.status_code})")
                    else:
                        st.error("❌ No se puede conectar al servidor. Verifica que el backend esté corriendo.")


def dashboard_page():
    """Main dashboard"""
    st.title("🏛️ Gestor Fiscal Personal")
    
    # Sidebar
    with st.sidebar:
        st.write(f"👤 {st.session_state.user['first_name']} {st.session_state.user['last_name']}")
        st.write(f"📧 {st.session_state.user['email']}")
        
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.token = None
            st.session_state.user = None
            st.query_params.clear()  # Clear persisted session
            st.rerun()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📋 Dashboard", 
        "👤 Perfil Fiscal", 
        "📄 Documentos",
        "🧾 CFDIs",
        "📊 Declaraciones",
        "🔐 Credenciales SAT",
        "💰 Prestaciones",
        "🔄 Sincronización"
    ])
    
    with tab1:
        show_dashboard()
    
    with tab2:
        show_fiscal_profile()
    
    with tab3:
        show_documents()
    
    with tab4:
        show_cfdis()
    
    with tab5:
        show_declaraciones()
    
    with tab6:
        show_sat_credentials()
    
    with tab7:
        show_prestaciones()
    
    with tab8:
        show_sync()


def show_sync():
    """Sincronización SAT - Download data from SAT portal"""
    st.header("🔄 Sincronización SAT")
    
    st.markdown("""
    Descarga automáticamente tus datos del portal del SAT:
    - 📥 Facturas (CFDIs) emitidas y recibidas
    - 📊 Constancia de situación fiscal
    - 💰 Información para declaraciones
    """)
    
    # Check if credentials exist
    creds_response = api_request("/credentials/sat")
    has_credentials = (creds_response and 
                       creds_response.status_code == 200 and 
                       creds_response.json().get('has_credentials', False))
    
    if not has_credentials:
        st.warning("⚠️ Primero configura tus credenciales SAT en la pestaña **'🔐 Credenciales SAT'**")
        return
    
    st.divider()
    
    # Sync options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### ¿Qué hace la sincronización?
        
        - 📥 Descarga todas tus facturas (CFDIs)
        - 📊 Calcula tus declaraciones automáticamente  
        - 💰 Muestra cuánto has ganado y gastado
        - 🎯 Te dice si te deben dinero o debes impuestos
        
        **Toma unos minutos la primera vez**, luego es instantáneo.
        """)
    
    with col2:
        months_back = st.number_input("Meses atrás", min_value=1, max_value=24, value=12)
        
        if st.button("🔄 Sincronizar Ahora", type="primary", use_container_width=True):
            with st.spinner("Iniciando sincronización..."):
                try:
                    sync_response = api_request("/sync/start", "POST", {"months_back": months_back})
                    
                    if sync_response and sync_response.status_code == 200:
                        st.success("✅ ¡Sincronización iniciada!")
                        
                        # Poll for status updates
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        import time
                        for i in range(20):  # Check for ~1 minute max
                            time.sleep(3)
                            
                            status_check = api_request("/sync/status")
                            if status_check and status_check.status_code == 200:
                                status_data = status_check.json()
                                
                                if status_data.get('status') == 'running':
                                    progress_bar.progress(min(0.95, (i + 1) / 20))
                                    status_text.info("⏳ Descargando facturas del SAT...")
                                
                                elif status_data.get('status') == 'completed':
                                    progress_bar.progress(1.0)
                                    
                                    # Show summary
                                    results = status_data.get('results', {})
                                    st.success(f"""
                                    🎉 **¡Sincronización completada!**
                                    
                                    📊 **Resumen:**
                                    - ✅ Facturas procesadas: {results.get('cfdis_processed', 0)}
                                    - 📤 Emitidas: {results.get('cfdis_emitidos', 0)} (${results.get('total_ingresos', 0):,.2f})
                                    - 📥 Recibidas: {results.get('cfdis_recibidos', 0)} (${results.get('total_egresos', 0):,.2f})
                                    - ⏱️ Duración: {status_data.get('duration_seconds', 0)} segundos
                                    """)
                                    break
                                
                                elif status_data.get('status') == 'failed':
                                    error_msg = status_data.get('error_message', 'Unknown error')
                                    st.error(f"❌ Error: {error_msg}")
                                    
                                    # If session expired, offer to clear it
                                    if 'session expired' in error_msg.lower() or 'manual login required' in error_msg.lower():
                                        st.warning("💡 Tu sesión con el SAT ha expirado.")
                                        if st.button("🔄 Limpiar sesión y reintentar", type="primary"):
                                            clear_response = api_request("/credentials/sat/clear-session", "POST")
                                            if clear_response and clear_response.status_code == 200:
                                                st.success("✅ Sesión limpiada. Ahora valida tus credenciales de nuevo en la pestaña 'Credenciales SAT'")
                                                st.info("👉 Ve a **'🔐 Credenciales SAT'** → Click en **'Validar Credenciales'**")
                                            else:
                                                st.error("Error al limpiar sesión")
                                    break
                        else:
                            st.info("💡 La sincronización sigue en progreso. Puedes refrescar esta pestaña en unos minutos para ver los resultados.")
                            
                    elif sync_response:
                        # Got response but not 200
                        try:
                            error_detail = sync_response.json()
                            error_msg = error_detail.get("detail", str(error_detail))
                        except:
                            error_msg = f"Error HTTP {sync_response.status_code}: {sync_response.text}"
                        
                        st.error(f"❌ {error_msg}")
                        
                        with st.expander("🔍 Más información"):
                            st.code(f"Status: {sync_response.status_code}\nResponse: {sync_response.text}")
                    else:
                        # No response at all
                        st.error("❌ No se pudo conectar con el servidor. Verifica que el backend esté corriendo.")
                except Exception as e:
                    st.error(f"❌ Error inesperado: {str(e)}")
                    st.exception(e)
    
    st.divider()
    
    # Utilities section
    with st.expander("🔧 Herramientas"):
        st.markdown("**Limpiar sesión guardada**")
        st.caption("Usa esto si la sincronización falla por sesión expirada")
        
        if st.button("🗑️ Borrar sesión SAT guardada"):
            clear_response = api_request("/credentials/sat/clear-session", "POST")
            if clear_response and clear_response.status_code == 200:
                st.success("✅ Sesión limpiada. La próxima sincronización abrirá el navegador para login manual.")
            else:
                st.error("❌ Error al limpiar sesión")
    
    st.divider()
    
    # Show last sync status
    st.subheader("📊 Historial de Sincronizaciones")
    
    status_check = api_request("/sync/status")
    if status_check and status_check.status_code == 200:
        status_data = status_check.json()
        
        if status_data.get('has_synced'):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Estado", status_data.get('status', 'Unknown').upper())
            
            with col2:
                started = status_data.get('started_at', 'N/A')
                if started != 'N/A':
                    from datetime import datetime
                    dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                    started = dt.strftime('%Y-%m-%d %H:%M')
                st.metric("Última sincronización", started)
            
            with col3:
                st.metric("Total CFDIs en BD", status_data.get('total_cfdis_db', 0))
            
            # Show results if completed
            if status_data.get('status') == 'completed':
                results = status_data.get('results', {})
                st.success(f"""
                **Última sincronización exitosa:**
                - Procesadas: {results.get('cfdis_processed', 0)}
                - Emitidas: {results.get('cfdis_emitidos', 0)} (${results.get('total_ingresos', 0):,.2f})
                - Recibidas: {results.get('cfdis_recibidos', 0)} (${results.get('total_egresos', 0):,.2f})
                """)
        else:
            st.info("ℹ️ Aún no has realizado ninguna sincronización")


def show_dashboard():
    """Dashboard overview - SAT for Dummies style"""
    st.header("🏠 Mi Panel SAT")
    st.caption("Tu información fiscal en lenguaje sencillo")
    
    # Check if RFC is configured first
    profile_response = api_request("/fiscal/profile")
    has_rfc = False
    if profile_response and profile_response.status_code == 200:
        profile = profile_response.json()
        has_rfc = profile.get('rfc') and profile.get('rfc') != ''
    
    # If no RFC, show setup wizard
    if not has_rfc:
        st.warning("👋 ¡Bienvenido! Para empezar, necesito que configures tu RFC")
        
        with st.expander("📋 ¿Qué es el RFC?", expanded=True):
            st.markdown("""
            El **RFC** (Registro Federal de Contribuyentes) es tu identificador único ante el SAT.
            
            Es como tu "número de cliente" con el SAT. Sin él no puedo conectarme a tu cuenta.
            
            **Ejemplo de RFC:**
            - Personas: `XAXX010101000`
            - Empresas: `ABC123456789`
            
            Lo encuentras en:
            - Tu cédula fiscal
            - Tu constancia de situación fiscal
            - Cualquier factura que hayas emitido o recibido
            """)
        
        st.info("👉 Ve a la pestaña **'Perfil Fiscal'** para configurar tu RFC")
        
        return
    
    # Check sync status
    sync_status = api_request("/sync/status")
    has_data = sync_status and sync_status.status_code == 200 and sync_status.json().get('has_synced')
    
    # Check if credentials are configured properly
    creds_response = api_request("/credentials/sat")
    has_credentials = (creds_response and 
                       creds_response.status_code == 200 and 
                       creds_response.json().get('has_credentials', False))
    
    # Setup wizard if no credentials
    if not has_credentials:
        st.warning("👋 ¡Bienvenido! Para empezar, necesito que configures tus datos del SAT")
        
        with st.expander("📋 ¿Qué necesito?", expanded=True):
            st.markdown("""
            Solo necesitas 2 cosas que ya tienes:
            
            1. **Tu RFC** - El número que te dio el SAT
            2. **Tu contraseña del SAT** - La que usas en sat.gob.mx
            
            Con esto, la app descargará toda tu información automáticamente. 
            ¡Es como magia! ✨
            """)
        
        if st.button("➡️ Configurar mis datos SAT", type="primary", use_container_width=True):
            st.switch_page  # Would navigate to credentials tab
            st.info("👆 Ve a la pestaña 'Credenciales SAT' arriba")
        
        return
    
    # Sync button if credentials exist but no data
    if not has_data:
        st.info("✅ Credenciales configuradas. Ahora sincroniza tus datos del SAT.")
        
        st.markdown("""
        ### 🔄 Próximo paso: Sincronizar datos
        
        Ve a la pestaña **'🔄 Sincronización'** para descargar tus facturas del SAT.
        
        La primera sincronización toma unos minutos, pero después es instantánea.
        """)
        
        st.info("👉 Haz clic en la pestaña **'🔄 Sincronización'** arriba para continuar")
        
        return
    
    # Main dashboard with data
    st.success("✅ Datos sincronizados con el SAT")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    # Get stats from API
    stats_response = api_request("/cfdis/stats")
    stats = stats_response.json() if stats_response and stats_response.status_code == 200 else {}
    
    with col1:
        st.metric(
            "💰 Ingresos",
            f"${stats.get('total_ingresos', 0):,.0f}",
            help="Total de dinero que has recibido"
        )
    
    with col2:
        st.metric(
            "💸 Gastos", 
            f"${stats.get('total_egresos', 0):,.0f}",
            help="Total de gastos deducibles"
        )
    
    with col3:
        st.metric(
            "📄 Facturas",
            f"{stats.get('total_cfdis', 0):,}",
            help="Número total de CFDIs"
        )
    
    with col4:
        st.metric(
            "✅ Deducibles",
            f"{stats.get('deducibles', 0):,}",
            help="Gastos que puedes descontar de impuestos"
        )
    
    st.divider()
    
    # Quick actions
    st.subheader("⚡ Acciones Rápidas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Ver Declaraciones", use_container_width=True):
            st.info("👆 Ve a la pestaña 'Declaraciones'")
    
    with col2:
        if st.button("💰 Ver Deducciones", use_container_width=True):
            st.info("👆 Ve a la pestaña 'Prestaciones'")
    
    with col3:
        if st.button("🔄 Actualizar Datos", use_container_width=True, key="quick_sync"):
            with st.spinner("Actualizando..."):
                sync_response = api_request("/sync/quick", "POST")
                if sync_response and sync_response.status_code == 200:
                    st.success("✅ Actualización iniciada")
    
    st.divider()
    
    # Simple explanation section
    with st.expander("❓ ¿Qué significa todo esto?"):
        st.markdown("""
        ### Conceptos simples
        
        - **Ingresos**: Todo el dinero que has recibido (ventas, pagos, salario)
        - **Gastos deducibles**: Compras que puedes usar para pagar menos impuestos
        - **Declaraciones**: Reportes que le mandas al SAT de cuánto ganaste
        - **Saldo a favor**: El SAT te debe dinero 💚
        - **Saldo a cargo**: Tú le debes al SAT 💳
        
        ### ¿Necesitas ayuda?
        - Todas las secciones tienen explicaciones sencillas
        - Los números se calculan automáticamente
        - No necesitas ser contador para usar esta app
        """)


def show_fiscal_profile():
    """Fiscal profile management"""
    st.header("👤 Mi Perfil Fiscal")
    st.caption("Tu información básica ante el SAT")
    
    user = st.session_state.user
    
    # Get fiscal profile
    response = api_request("/fiscal/profile")
    
    if response and response.status_code == 200:
        profile = response.json()
        
        # Check if RFC is configured
        has_rfc = profile.get('rfc') and profile.get('rfc') != ''
        
        if not has_rfc:
            st.warning("⚠️ **Importante:** Necesitas configurar tu RFC para usar la sincronización automática del SAT")
        
        # If RFC is missing, force edit mode
        has_rfc = profile.get('rfc') and profile.get('rfc') != ''
        
        # Display mode vs Edit mode
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("Datos Personales")
        with col2:
            if has_rfc:
                edit_mode = st.button("✏️ Editar", use_container_width=True)
            else:
                edit_mode = True
                st.warning("⚠️ Completa tu RFC")
        
        if not edit_mode and has_rfc:
            # Display mode - Show info cleanly
            st.divider()
            
            # Personal Information
            st.subheader("📋 Información Personal")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**👤 Nombre Completo**")
                st.text(f"{user.get('first_name', '')} {user.get('last_name', '')}")
                
                st.markdown("**📧 Correo Electrónico**")
                st.text(user.get('email', 'No registrado'))
            
            with col2:
                st.markdown("**📱 Teléfono**")
                st.text(user.get('phone', 'No registrado'))
                
                st.markdown("**🎂 CURP**")
                st.text(profile.get('curp', 'No registrado'))
            
            with col3:
                st.markdown("**📅 Miembro desde**")
                created_at = user.get('created_at', '')
                if created_at:
                    from datetime import datetime
                    try:
                        date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        st.text(date_obj.strftime('%d/%m/%Y'))
                    except:
                        st.text('N/A')
                else:
                    st.text('N/A')
                
                st.markdown("**✅ Estado**")
                status = user.get('status', 'unknown')
                status_text = {
                    'active': '✅ Activo',
                    'inactive': '❌ Inactivo',
                    'pending_verification': '⏳ Pendiente'
                }.get(status, status)
                st.text(status_text)
            
            st.divider()
            
            # Fiscal Information
            st.subheader("🏛️ Información Fiscal")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🆔 RFC**")
                st.text(profile.get('rfc', 'No registrado'))
                
                st.markdown("**📝 Nombre/Razón Social**")
                st.text(profile.get('legal_name', 'No registrado'))
            
            with col2:
                st.markdown("**💼 Régimen Fiscal**")
                regime = profile.get('tax_regime', 'No registrado')
                regime_names = {
                    '605': 'Sueldos y Salarios',
                    '621': 'Incorporación Fiscal',
                    '626': 'RESICO',
                    '612': 'Actividades Empresariales',
                    '606': 'Arrendamiento',
                    '601': 'Régimen General',
                    '616': 'Sin Obligaciones'
                }
                regime_text = f"{regime} - {regime_names.get(regime, '')}" if regime != 'No registrado' else regime
                st.text(regime_text)
                
                st.markdown("**📊 Situación Fiscal**")
                fiscal_status = profile.get('fiscal_status', 'unknown')
                status_display = {
                    'active': '✅ Al corriente',
                    'pending': '⏳ Pendiente',
                    'suspended': '⚠️ Suspendido',
                    'cancelled': '❌ Cancelado',
                    'unknown': '❓ Desconocido'
                }.get(fiscal_status, fiscal_status)
                st.text(status_display)
            
            st.divider()
            
            # Address
            st.subheader("🏠 Domicilio Fiscal")
            if profile.get('fiscal_address'):
                addr = profile.get('fiscal_address')
                if isinstance(addr, dict):
                    st.text(f"{addr.get('street', '')} {addr.get('number', '')}")
                    st.text(f"{addr.get('colony', '')}, {addr.get('city', '')}")
                    st.text(f"{addr.get('state', '')} - CP: {addr.get('zip', '')}")
                else:
                    st.text(addr)
            else:
                st.text("No registrado")
            
        else:
            # Edit mode
            with st.form("fiscal_form"):
                st.subheader("Editar Información")
                
                # Personal Info Section
                st.markdown("### 👤 Datos Personales")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    first_name = st.text_input("Nombre *", value=user.get("first_name", ""), help="Tu nombre(s)")
                    email = st.text_input("Email *", value=user.get("email", ""), help="Tu correo electrónico", disabled=True)
                
                with col2:
                    last_name = st.text_input("Apellidos *", value=user.get("last_name", ""), help="Tus apellidos")
                    phone = st.text_input("Teléfono", value=user.get("phone", ""), help="10 dígitos", max_chars=10)
                
                with col3:
                    curp = st.text_input("CURP", value=profile.get("curp", ""), max_chars=18, help="Clave Única de Registro de Población")
                    st.caption("¿No lo sabes? [Consulta tu CURP aquí](https://www.gob.mx/curp/)")
                
                st.divider()
                
                # Fiscal Info Section
                st.markdown("### 🏛️ Información Fiscal")
                
                rfc = st.text_input("RFC *", value=profile.get("rfc", ""), max_chars=13, help="13 caracteres. Personas físicas: primeros 13 de tu CURP. Personas morales: tu RFC empresarial")
                st.caption("💡 Persona física: usa los primeros 13 caracteres de tu CURP")
                legal_name = st.text_input("Nombre/Razón Social *", value=profile.get("legal_name", ""), help="Nombre completo o nombre de empresa")
                
                tax_regime_options = [
                    "605 - Sueldos y Salarios",
                    "621 - Incorporación Fiscal",
                    "626 - Régimen Simplificado de Confianza (RESICO)",
                    "612 - Actividades Empresariales y Profesionales",
                    "606 - Arrendamiento",
                    "601 - Régimen General (Personas Morales)",
                    "616 - Sin Obligaciones Fiscales"
                ]
                
                # Find current selection
                current_regime = profile.get("tax_regime") or ""
                default_index = 0
                for i, opt in enumerate(tax_regime_options):
                    if current_regime and opt.startswith(current_regime):
                        default_index = i
                        break
                
                tax_regime = st.selectbox("Régimen Fiscal *", tax_regime_options, index=default_index, help="Tu régimen ante el SAT")
                
                st.divider()
                
                # Address Section
                st.markdown("### 🏠 Domicilio Fiscal")
                
                # Check if fiscal_address is dict or string
                addr = profile.get('fiscal_address', {})
                if isinstance(addr, str):
                    addr = {}
                
                col1, col2 = st.columns(2)
                with col1:
                    street = st.text_input("Calle", value=addr.get('street', '') if addr else '', help="Nombre de la calle")
                    colony = st.text_input("Colonia", value=addr.get('colony', '') if addr else '', help="Nombre de la colonia")
                    city = st.text_input("Ciudad/Municipio", value=addr.get('city', '') if addr else '')
                
                with col2:
                    number = st.text_input("Número", value=addr.get('number', '') if addr else '', help="Número exterior e interior")
                    state = st.text_input("Estado", value=addr.get('state', '') if addr else '', help="Estado de la República")
                    zip_code = st.text_input("Código Postal", value=addr.get('zip', '') if addr else '', max_chars=5, help="5 dígitos")
                
                st.divider()
                
                col1, col2 = st.columns(2)
                with col1:
                    submit = st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True)
                with col2:
                    cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)
                
                if submit:
                    regime_code = tax_regime.split(" - ")[0]
                    
                    # Build address dict
                    fiscal_address_dict = {
                        'street': street,
                        'number': number,
                        'colony': colony,
                        'city': city,
                        'state': state,
                        'zip': zip_code
                    } if any([street, number, colony, city, state, zip_code]) else None
                    
                    # Update user info
                    user_update = api_request("/users/profile", "PUT", {
                        "first_name": first_name if first_name else None,
                        "last_name": last_name if last_name else None,
                        "phone": phone if phone else None
                    })
                    
                    # Update fiscal profile
                    profile_update = api_request("/fiscal/profile", "PUT", {
                        "rfc": rfc if rfc else None,
                        "curp": curp if curp else None,
                        "legal_name": legal_name if legal_name else None,
                        "tax_regime": regime_code,
                        "fiscal_address": fiscal_address_dict
                    })
                    
                    if user_update and user_update.status_code == 200 and profile_update and profile_update.status_code == 200:
                        st.success("✅ Perfil actualizado correctamente")
                        # Update session state
                        st.session_state.user = user_update.json()
                        st.rerun()
                    else:
                        st.error("❌ Error al actualizar el perfil")
                
                if cancel:
                    st.rerun()
    
    elif response and response.status_code == 404:
        st.warning("📝 Aún no tienes perfil fiscal. ¡Vamos a crearlo!")
        
        st.info("""
        ### ¿Qué es esto?
        
        Tu perfil fiscal es tu "tarjeta de presentación" ante el SAT.
        Solo necesitas tu RFC y nombre completo para empezar.
        """)
        
        with st.form("fiscal_form_new"):
            st.subheader("Crear Mi Perfil")
            
            col1, col2 = st.columns(2)
            
            with col1:
                rfc = st.text_input("RFC *", max_chars=13, help="Ejemplo: XAXX010101000")
                legal_name = st.text_input("Nombre Completo *", help="Como aparece en tu cédula fiscal")
            
            with col2:
                curp = st.text_input("CURP", max_chars=18, help="Opcional, pero recomendado")
                tax_regime = st.selectbox("Régimen Fiscal", [
                    "605 - Sueldos y Salarios",
                    "626 - Régimen Simplificado de Confianza (RESICO)",
                    "612 - Actividades Empresariales y Profesionales",
                    "606 - Arrendamiento"
                ])
            
            submit = st.form_submit_button("✅ Crear Perfil", type="primary", use_container_width=True)
            
            if submit:
                if not rfc or not legal_name:
                    st.error("❌ RFC y nombre son obligatorios")
                else:
                    regime_code = tax_regime.split(" - ")[0]
                    
                    create_response = api_request("/fiscal/profile", "POST", {
                        "rfc": rfc,
                        "curp": curp if curp else None,
                        "legal_name": legal_name,
                        "tax_regime": regime_code
                    })
                    
                    if create_response and create_response.status_code == 200:
                        st.success("✅ ¡Perfil creado! Ahora puedes configurar tus credenciales SAT")
                        st.rerun()
                    else:
                        error_msg = create_response.json().get("detail", "Error al crear perfil") if create_response else "Error de conexión"
                        st.error(f"❌ {error_msg}")
    
    else:
        st.error("❌ Error al cargar perfil")


def show_documents():
    """Documents management"""
    st.header("📄 Mis Documentos")
    
    st.info("🚧 Sección de documentos en desarrollo")
    
    # Upload section
    st.subheader("📤 Subir Documento")
    
    with st.form("upload_form"):
        doc_type = st.selectbox("Tipo de Documento", [
            "Constancia de Situación Fiscal",
            "e.firma (Certificado .cer)",
            "e.firma (Llave .key)",
            "CFDI",
            "Opinión de Cumplimiento",
            "Otro"
        ])
        
        title = st.text_input("Título del Documento")
        file = st.file_uploader("Seleccionar Archivo")
        
        submit = st.form_submit_button("📤 Subir")
        
        if submit and file:
            st.success(f"✅ Documento '{title}' preparado para subir (API endpoint pendiente)")


def show_sat_credentials():
    """SAT credentials management - Simplified"""
    st.header("🔐 Mis Credenciales del SAT")
    st.caption("Esto es lo que usas para entrar a sat.gob.mx")
    
    st.info("""  
    ### 🔒 ¿Es seguro?
    
    Sí. Tus credenciales se guardan encriptadas (AES-256) como en los bancos.
    Nadie puede verlas, ni siquiera nosotros.
    """)
    
    # Check if credentials exist
    response = api_request("/credentials/sat", "GET")
    
    if response and response.status_code == 200:
        creds = response.json()
        
        if creds.get("has_credentials"):
            st.success("✅ Credenciales SAT configuradas")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Contraseña SAT", "Configurada ✓" if creds.get("has_password") else "No")
            with col2:
                efirma_status = "Configurada ✓" if creds.get("has_efirma") else "No"
                st.metric("e.firma", efirma_status)
            with col3:
                if creds.get("last_validated"):
                    st.metric("Última validación", creds.get("last_validated"))
            
            # Warning if e.firma exists
            if creds.get("has_efirma"):
                st.warning("⚠️ Tienes e.firma configurada. Si está vencida, elimínala abajo para usar solo contraseña SAT.")
            
            st.divider()
            
            # Test connection button (always visible)
            st.subheader("🧪 Probar Conexión")
            if st.button("🔍 Validar Credenciales con el SAT", use_container_width=True):
                with st.spinner("Conectando al portal SAT..."):
                    test_response = api_request("/credentials/validate")
                    
                    if test_response and test_response.status_code == 200:
                        result = test_response.json()
                        if result.get("valid"):
                            st.success("✅ ¡Conexión exitosa! Tus credenciales funcionan correctamente")
                            st.info(f"✓ RFC: {result.get('rfc', 'N/A')}")
                        else:
                            st.error(f"❌ Credenciales inválidas: {result.get('message', 'Error desconocido')}")
                    elif test_response:
                        st.error(f"❌ Error: {test_response.json().get('detail', 'Error de validación')}")
                    else:
                        st.error("❌ No se pudo conectar con el servidor")
            
            st.divider()
            
            # Options to manage credentials
            st.subheader("⚙️ Administrar Credenciales")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✏️ Editar Credenciales", use_container_width=True, type="primary"):
                    st.session_state.show_update_creds = True
            with col2:
                # Only show e.firma delete if it exists
                if creds.get("has_efirma"):
                    if st.button("🔓 Eliminar e.firma", use_container_width=True, help="Conserva tu contraseña SAT"):
                        delete_efirma = api_request("/credentials/efirma", "DELETE")
                        if delete_efirma and delete_efirma.status_code == 200:
                            st.success("✅ e.firma eliminada. Ahora solo usarás contraseña SAT.")
                            st.rerun()
                        else:
                            st.error("❌ Error al eliminar e.firma")
            with col3:
                if st.button("🗑️ Eliminar Todo", use_container_width=True):
                    if st.session_state.get("confirm_delete"):
                        delete_response = api_request("/credentials/sat", "DELETE")
                        if delete_response and delete_response.status_code == 200:
                            st.success("✅ Credenciales eliminadas")
                            st.session_state.confirm_delete = False
                            st.rerun()
                        else:
                            st.error("❌ Error al eliminar credenciales")
                    else:
                        st.session_state.confirm_delete = True
                        st.rerun()
            
            if st.session_state.get("confirm_delete"):
                st.warning("⚠️ ¿Estás seguro? Haz clic de nuevo en 'Eliminar Credenciales' para confirmar.")
            
            # Update form (expanded view)
            if st.session_state.get("show_update_creds"):
                st.divider()
                st.subheader("✏️ Editar Credenciales")
                
                with st.form("update_sat_creds_form"):
                    st.markdown("### 1️⃣ Contraseña SAT")
                    new_password = st.text_input(
                        "Nueva contraseña del portal SAT", 
                        type="password",
                        help="Déjalo en blanco si no quieres cambiarla"
                    )
                    st.caption("¿Olvidaste tu contraseña? [Recupérala aquí](https://www.sat.gob.mx/aplicacion/53027/recupera-tu-contrasena)")
                    
                    st.divider()
                    st.markdown("### 2️⃣ e.firma (Obligatoria para sincronización SAT)")
                    st.caption("⚠️ Sin e.firma no podrás descargar CFDIs del SAT")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_cer = st.file_uploader("Nuevo certificado .cer", type=["cer"], key="update_cer")
                    with col2:
                        new_key = st.file_uploader("Nueva llave .key", type=["key"], key="update_key")
                    
                    if new_cer and new_key:
                        new_efirma_password = st.text_input(
                            "Contraseña de la e.firma",
                            type="password",
                            help="La contraseña con la que protegiste tus archivos .cer y .key"
                        )
                    
                    col_submit, col_cancel = st.columns(2)
                    with col_submit:
                        submit = st.form_submit_button("💾 Guardar Cambios", use_container_width=True, type="primary")
                    with col_cancel:
                        cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)
                    
                    if cancel:
                        st.session_state.show_update_creds = False
                        st.rerun()
                    
                    if submit:
                        # Prepare update data
                        update_data = {}
                        files_data = {}
                        
                        if new_password:
                            update_data["sat_password"] = new_password
                        
                        if new_cer and new_key:
                            if not new_efirma_password:
                                st.error("❌ Debes proporcionar la contraseña de la e.firma")
                            else:
                                files_data = {
                                    "cer_file": ("certificate.cer", new_cer.getvalue(), "application/x-x509-ca-cert"),
                                    "key_file": ("private_key.key", new_key.getvalue(), "application/octet-stream")
                                }
                                update_data["efirma_password"] = new_efirma_password
                        
                        # Make update request
                        if update_data or files_data:
                            if files_data:
                                # Use multipart form data for files
                                update_response = api_request("/credentials/sat", "PUT", data=update_data, files=files_data)
                            else:
                                # Use JSON for password only
                                update_response = api_request("/credentials/sat", "PUT", update_data)
                            
                            if update_response and update_response.status_code == 200:
                                st.success("✅ Credenciales actualizadas correctamente")
                                st.session_state.show_update_creds = False
                                st.rerun()
                            else:
                                error_detail = update_response.json().get("detail", "Error desconocido") if update_response else "No se pudo conectar"
                                st.error(f"❌ Error al actualizar: {error_detail}")
                        else:
                            st.warning("⚠️ No hay cambios para guardar")
        else:
            st.markdown("""
            ### 📝 Primera vez aquí
            
            Solo necesitas 2 cosas:
            
            1. **RFC** - Ya está en tu perfil fiscal
            2. **Contraseña del SAT** - La que usas en sat.gob.mx
            3. **e.firma** - Obligatoria para descargar CFDIs del SAT
            
            ⚠️ **Sin e.firma no podrás sincronizar datos del SAT** (descarga masiva de facturas).
            """)
            
            with st.form("sat_creds_form"):
                st.subheader("Paso 1: Contraseña SAT (Obligatorio)")
                sat_password = st.text_input(
                    "Contraseña del portal sat.gob.mx",
                    type="password",
                    help="La misma que usas para entrar al portal"
                )
                st.caption("¿Olvidaste tu contraseña? [Recupérala aquí](https://www.sat.gob.mx/aplicacion/53027/recupera-tu-contrasena)")
                
                st.divider()
                st.subheader("Paso 2: e.firma (Obligatoria para sincronización)")
                st.caption("⚠️ Necesaria para descargar CFDIs del SAT mediante Web Services")
                
                with st.expander("¿Qué es la e.firma?"):
                    st.markdown("""
                    Es como tu firma física pero digital. Sirve para:
                    - **Descargar CFDIs del SAT** (obligatorio)
                    - Firmar documentos oficiales
                    - Timbrar facturas
                    - Autenticar Web Services del SAT
                    
                    **Es OBLIGATORIA** para sincronizar con el SAT mediante Web Services.
                    """)
                
                col1, col2 = st.columns(2)
                with col1:
                    cer_file = st.file_uploader("Certificado .cer", type=["cer"])
                with col2:
                    key_file = st.file_uploader("Llave .key", type=["key"])
                
                # Campo de contraseña siempre habilitado
                efirma_password = st.text_input(
                    "Contraseña e.firma",
                    type="password",
                    key="efirma_pwd",
                    help="Contraseña de tu e.firma (obligatoria si subes archivos)",
                    placeholder="Ingresa la contraseña de tu e.firma"
                )
                
                submit = st.form_submit_button("💾 Guardar y Continuar", type="primary", use_container_width=True)
                
                if submit:
                    if not sat_password:
                        st.error("❌ Necesitas ingresar tu contraseña del SAT")
                    elif cer_file and key_file and not efirma_password:
                        st.error("❌ Si subes archivos e.firma, la contraseña es obligatoria")
                    else:
                        # Save SAT password
                        save_response = api_request("/credentials/sat", "POST", {
                            "sat_password": sat_password,
                            "rfc": None
                        })
                        
                        if save_response and save_response.status_code in [200, 201]:
                            st.success("✅ Contraseña guardada")
                            
                            # Upload e.firma if provided
                            if cer_file and key_file and efirma_password:
                                files = {
                                    "cer_file": cer_file,
                                    "key_file": key_file
                                }
                                data = {"efirma_password": efirma_password}
                                
                                efirma_response = api_request("/credentials/efirma/upload", "POST", data=data, files=files)
                                if efirma_response and efirma_response.status_code in [200, 201]:
                                    st.success("✅ e.firma guardada también")
                            
                            st.success("🎉 ¡Listo! Ahora ve al Dashboard para sincronizar tus datos")
                            st.rerun()
                        else:
                            st.error("❌ Error al guardar. Verifica tu contraseña")
    else:
        st.error("❌ Error al conectar con el servidor")


def show_declaraciones():
    """Tax Declarations view - Similar to SAT email notifications"""
    st.header("📊 Declaraciones Fiscales")
    
    # Get available periods
    periodos_response = api_request("/declaraciones/disponibles")
    
    if not periodos_response or periodos_response.status_code != 200:
        st.warning("⚠️ No hay datos de CFDIs disponibles. Sube tus facturas primero en la sección CFDIs.")
        return
    
    periodos_data = periodos_response.json()
    periodos = periodos_data.get('periodos_disponibles', [])
    
    if not periodos:
        st.info("📤 No tienes CFDIs cargados aún. Ve a la sección CFDIs para subirlos.")
        return
    
    # Year selector
    years = [p['year'] for p in periodos]
    selected_year = st.selectbox("📅 Año Fiscal", years, index=0, key="declaraciones_year_selector")
    
    # Get months available for selected year
    selected_periodo = next((p for p in periodos if p['year'] == selected_year), None)
    meses = selected_periodo.get('meses', []) if selected_periodo else []
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📆 Declaraciones Mensuales", "📊 Declaración Anual", "📈 Resumen"])
    
    with tab1:
        st.subheader(f"Declaraciones Mensuales {selected_year}")
        st.caption("Similar a las notificaciones que recibes del SAT por correo")
        
        if not meses:
            st.info("No hay datos para este año")
        else:
            # Month selector
            mes_nombres = {m['mes']: m['mes_nombre'] for m in meses}
            selected_month = st.selectbox(
                "Selecciona mes",
                options=list(mes_nombres.keys()),
                format_func=lambda x: mes_nombres[x],
                key="mes_selector"
            )
            
            # Get monthly declaration
            with st.spinner("Cargando declaración mensual..."):
                decl_response = api_request(f"/declaraciones/mensual/{selected_year}/{selected_month}")
                
                if decl_response and decl_response.status_code == 200:
                    decl = decl_response.json()
                    
                    # Header with contributor info
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**RFC:** {decl['contribuyente']['rfc'] or 'No registrado'}")
                        st.markdown(f"**Nombre:** {decl['contribuyente']['nombre'] or 'No registrado'}")
                    with col2:
                        st.markdown(f"**Régimen:** {decl['contribuyente']['regimen'] or 'No registrado'}")
                        st.markdown(f"**Periodo:** {decl['periodo']['periodo_texto']}")
                    
                    st.divider()
                    
                    # Income section
                    st.subheader("💰 Ingresos")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Ingresos Totales", f"${decl['ingresos']['totales']:,.2f}")
                    with col2:
                        st.metric("Ingresos Gravados", f"${decl['ingresos']['gravados']:,.2f}")
                    with col3:
                        st.metric("IVA Cobrado", f"${decl['ingresos']['iva_cobrado']:,.2f}")
                    
                    # Expenses section
                    st.subheader("💸 Egresos")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Egresos Totales", f"${decl['egresos']['totales']:,.2f}")
                    with col2:
                        st.metric("Egresos Deducibles", f"${decl['egresos']['deducibles']:,.2f}")
                    with col3:
                        st.metric("IVA Pagado", f"${decl['egresos']['iva_pagado']:,.2f}")
                    
                    # Payroll section
                    if decl['nomina']['salarios'] > 0:
                        st.subheader("👔 Nómina")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Salarios", f"${decl['nomina']['salarios']:,.2f}")
                        with col2:
                            st.metric("ISR Retenido", f"${decl['nomina']['isr_retenido']:,.2f}")
                    
                    # Taxes section
                    st.divider()
                    st.subheader("🏛️ Impuestos")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**IVA**")
                        iva_info = decl['impuestos']['iva']
                        st.metric("IVA Neto", f"${iva_info['neto']:,.2f}")
                        
                        if iva_info['a_cargo'] > 0:
                            st.error(f"💳 IVA a Cargo: ${iva_info['a_cargo']:,.2f}")
                        elif iva_info['a_favor'] > 0:
                            st.success(f"💚 IVA a Favor: ${iva_info['a_favor']:,.2f}")
                        else:
                            st.info("✅ IVA neutro (sin saldo)")
                    
                    with col2:
                        st.markdown("**ISR**")
                        isr_info = decl['impuestos']['isr']
                        st.metric("Base ISR", f"${isr_info['base']:,.2f}")
                        st.metric("ISR Retenido", f"${isr_info['retenido']:,.2f}")
                        st.caption("💡 El cálculo completo de ISR se realiza en la declaración anual")
                    
                    # Summary
                    st.divider()
                    st.subheader("📊 Resumen")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Utilidad Bruta", f"${decl['resumen']['utilidad_bruta']:,.2f}")
                    with col2:
                        total_cargo = decl['resumen']['total_impuestos_cargo']
                        total_favor = decl['resumen']['total_impuestos_favor']
                        if total_cargo > 0:
                            st.metric("Total a Cargo", f"${total_cargo:,.2f}", delta=None, delta_color="inverse")
                        elif total_favor > 0:
                            st.metric("Total a Favor", f"${total_favor:,.2f}", delta=None, delta_color="normal")
                    
                    # CFDIs used
                    st.divider()
                    st.caption(f"📄 Calculado con {decl['cfdis_count']['total']} CFDIs: "
                             f"{decl['cfdis_count']['ingresos']} ingresos, "
                             f"{decl['cfdis_count']['egresos']} egresos, "
                             f"{decl['cfdis_count']['nominas']} nóminas")
                    st.caption(f"🕐 Última actualización: {decl['fecha_calculo']}")
                    
                else:
                    st.error("Error al cargar declaración mensual")
    
    with tab2:
        st.subheader(f"Declaración Anual {selected_year}")
        st.caption("Resumen anual completo para tu declaración fiscal")
        
        with st.spinner("Cargando declaración anual..."):
            anual_response = api_request(f"/declaraciones/anual/{selected_year}")
            
            if anual_response and anual_response.status_code == 200:
                anual = anual_response.json()
                
                # Header
                st.divider()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**RFC:** {anual['contribuyente']['rfc'] or 'No registrado'}")
                with col2:
                    st.markdown(f"**Nombre:** {anual['contribuyente']['nombre'] or 'No registrado'}")
                with col3:
                    st.markdown(f"**Ejercicio:** {anual['ejercicio']}")
                
                st.divider()
                
                # Income breakdown
                st.subheader("💰 Ingresos Acumulables")
                ingresos = anual['ingresos']
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Salarios y Nómina", f"${ingresos['salarios_nomina']:,.2f}")
                    st.metric("Honorarios", f"${ingresos['honorarios']:,.2f}")
                    st.metric("Arrendamiento", f"${ingresos['arrendamiento']:,.2f}")
                with col2:
                    st.metric("Actividad Empresarial", f"${ingresos['actividad_empresarial']:,.2f}")
                    st.metric("Intereses", f"${ingresos['intereses']:,.2f}")
                    st.metric("Otros Ingresos", f"${ingresos['otros']:,.2f}")
                
                st.markdown(f"### **Total Ingresos: ${ingresos['total']:,.2f}**")
                
                st.divider()
                
                # Deductions breakdown
                st.subheader("📉 Deducciones Autorizadas")
                deducciones = anual['deducciones']
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Gastos Médicos", f"${deducciones['medicas']:,.2f}")
                    st.metric("Gastos Dentales", f"${deducciones['dentales']:,.2f}")
                    st.metric("Gastos Hospitalarios", f"${deducciones['hospitalarios']:,.2f}")
                    st.metric("Gastos Funerarios", f"${deducciones['funerarios']:,.2f}")
                    st.metric("Donativos", f"${deducciones['donativos']:,.2f}")
                with col2:
                    st.metric("Intereses Hipotecarios", f"${deducciones['intereses_hipotecarios']:,.2f}")
                    st.metric("Seguros Médicos", f"${deducciones['seguros_medicos']:,.2f}")
                    st.metric("Transporte Escolar", f"${deducciones['transporte_escolar']:,.2f}")
                    st.metric("Colegiaturas", f"${deducciones['educacion']:,.2f}")
                    st.metric("Otras Deducciones", f"${deducciones['otras']:,.2f}")
                
                st.markdown(f"### **Total Deducciones: ${deducciones['total']:,.2f}**")
                
                st.divider()
                
                # ISR Calculation
                st.subheader("🏛️ Impuesto Sobre la Renta (ISR)")
                impuestos = anual['impuestos']['isr']
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Base Gravable", f"${anual['impuestos']['base_gravable']:,.2f}")
                with col2:
                    st.metric("ISR Causado", f"${impuestos['causado']:,.2f}")
                with col3:
                    st.metric("ISR Retenido", f"${impuestos['retenido']:,.2f}")
                with col4:
                    saldo = impuestos['a_favor'] - impuestos['a_cargo']
                    if saldo > 0:
                        st.metric("Saldo a Favor", f"${abs(saldo):,.2f}", delta=None, delta_color="normal")
                    elif saldo < 0:
                        st.metric("Saldo a Cargo", f"${abs(saldo):,.2f}", delta=None, delta_color="inverse")
                    else:
                        st.metric("Saldo", "$0.00")
                
                st.divider()
                
                # Final summary
                st.subheader("📊 Resumen Final")
                resumen = anual['resumen']
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Ingresos Acumulables", f"${resumen['ingresos_acumulables']:,.2f}")
                with col2:
                    st.metric("Deducciones Autorizadas", f"${resumen['deducciones_autorizadas']:,.2f}")
                
                saldo_final = resumen['isr_cargo_favor']
                if saldo_final > 0:
                    st.success(f"### 💚 Saldo a Favor: ${saldo_final:,.2f}")
                    st.info("💡 Puedes solicitar devolución o compensación de este saldo")
                elif saldo_final < 0:
                    st.error(f"### 💳 Saldo a Cargo: ${abs(saldo_final):,.2f}")
                    st.warning("⚠️ Debes realizar el pago antes de la fecha límite")
                else:
                    st.info("### ✅ Sin saldo (declaración en ceros)")
                
                st.caption(f"🕐 Calculado el: {anual['fecha_calculo']}")
                
            else:
                st.error("Error al cargar declaración anual")
    
    with tab3:
        st.subheader(f"Resumen Completo {selected_year}")
        st.caption("Vista consolidada de todas las declaraciones del año")
        
        with st.spinner("Generando resumen..."):
            resumen_response = api_request(f"/declaraciones/resumen/{selected_year}")
            
            if resumen_response and resumen_response.status_code == 200:
                resumen = resumen_response.json()
                
                # Year totals
                st.divider()
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Ingresos Anuales", f"${resumen['totales']['ingresos_anuales']:,.2f}")
                with col2:
                    st.metric("Deducciones Anuales", f"${resumen['totales']['deducciones_anuales']:,.2f}")
                with col3:
                    st.metric("ISR Total", f"${resumen['totales']['isr_total']:,.2f}")
                with col4:
                    saldo = resumen['totales']['saldo_final']
                    if saldo > 0:
                        st.metric("Saldo Final a Favor", f"${saldo:,.2f}")
                    elif saldo < 0:
                        st.metric("Saldo Final a Cargo", f"${abs(saldo):,.2f}")
                    else:
                        st.metric("Saldo Final", "$0.00")
                
                st.divider()
                
                # Monthly breakdown table
                st.subheader("📅 Desglose Mensual")
                import pandas as pd
                
                mensuales = resumen['declaraciones_mensuales']
                df = pd.DataFrame(mensuales)
                df['mes_nombre'] = df['mes_nombre'].str.capitalize()
                df['ingresos'] = df['ingresos'].apply(lambda x: f"${x:,.2f}")
                df['egresos'] = df['egresos'].apply(lambda x: f"${x:,.2f}")
                df['iva_neto'] = df['iva_neto'].apply(lambda x: f"${x:,.2f}")
                
                st.dataframe(
                    df[['mes_nombre', 'ingresos', 'egresos', 'iva_neto', 'cfdis']],
                    column_config={
                        'mes_nombre': 'Mes',
                        'ingresos': 'Ingresos',
                        'egresos': 'Egresos',
                        'iva_neto': 'IVA Neto',
                        'cfdis': 'CFDIs'
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Download options
                st.divider()
                st.subheader("📥 Descargar")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📄 Descargar Declaración Anual (PDF)", use_container_width=True):
                        st.info("🚧 Función en desarrollo")
                with col2:
                    if st.button("📊 Exportar a Excel", use_container_width=True):
                        st.info("🚧 Función en desarrollo")
                
            else:
                st.error("Error al generar resumen")


def show_prestaciones():
    """Prestaciones y deducciones anuales"""
    st.header("💰 Prestaciones y Deducciones")
    
    st.info("📊 Visualiza tus prestaciones y deducciones fiscales por año")
    
    # Year selector
    current_year = datetime.now().year
    years = list(range(current_year, current_year - 10, -1))
    selected_year = st.selectbox("Año Fiscal", years, key="prestaciones_year_selector")
    
    # Fetch data from API
    response = api_request(f"/fiscal/prestaciones/{selected_year}")
    
    if not response or response.status_code != 200:
        st.warning(f"⚠️ No hay datos de prestaciones para {selected_year}. Sube CFDIs primero.")
        
        if st.button("📤 Ir a subir CFDIs"):
            st.session_state.active_tab = "cfdis"
            st.rerun()
        return
    
    data = response.json()
    ingresos = data.get('ingresos', {})
    deducciones = data.get('deducciones', {})
    impuestos = data.get('impuestos', {})
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📈 Ingresos", "📉 Deducciones", "📊 Resumen Anual"])
    
    with tab1:
        st.subheader(f"Ingresos {selected_year}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("💵 Ingresos Totales", f"${ingresos.get('total', 0):,.2f} MXN")
            st.metric("💼 Sueldos y Salarios", f"${ingresos.get('sueldos', 0):,.2f} MXN")
            st.metric("🏢 Actividad Empresarial", f"${ingresos.get('actividad_empresarial', 0):,.2f} MXN")
        
        with col2:
            st.metric("🏠 Arrendamiento", f"${ingresos.get('arrendamiento', 0):,.2f} MXN")
            st.metric("📈 Intereses", f"${ingresos.get('intereses', 0):,.2f} MXN")
            st.metric("➕ Otros Ingresos", f"${ingresos.get('otros', 0):,.2f} MXN")
        
        st.divider()
        
        # Ingresos por mes
        st.subheader("📅 Ingresos Mensuales")
        monthly_response = api_request(f"/fiscal/prestaciones/{selected_year}/monthly")
        
        if monthly_response and monthly_response.status_code == 200:
            monthly_data = monthly_response.json().get('monthly', [])
            
            months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
            table_data = {
                "Mes": months,
                "Ingresos": [f"${m['ingresos']:,.2f}" for m in monthly_data],
                "ISR Retenido": [f"${m['isr_retenido']:,.2f}" for m in monthly_data],
                "CFDIs": [m['total_cfdis'] for m in monthly_data]
            }
            st.dataframe(table_data, use_container_width=True)
    
    with tab2:
        st.subheader(f"Deducciones Autorizadas {selected_year}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("💊 Gastos Médicos", f"${deducciones.get('gastos_medicos', 0):,.2f} MXN")
            st.metric("🏠 Intereses Hipotecarios", f"${deducciones.get('intereses_hipotecarios', 0):,.2f} MXN")
            st.metric("🎓 Educación", f"${deducciones.get('educacion', 0):,.2f} MXN")
        
        with col2:
            st.metric("💰 Seguros", f"${deducciones.get('seguros', 0):,.2f} MXN")
            st.metric("🚗 Transporte Escolar", f"${deducciones.get('transporte_escolar', 0):,.2f} MXN")
            st.metric("🎁 Donativos", f"${deducciones.get('donativos', 0):,.2f} MXN")
        
        st.metric("➕ Otras Deducciones", f"${deducciones.get('otras', 0):,.2f} MXN")
        st.metric("📊 **Total Deducciones**", f"${deducciones.get('total', 0):,.2f} MXN")
        
        st.divider()
        
        # Detalle de deducciones
        if st.button("🔍 Ver Detalle de Deducciones"):
            detalle_response = api_request(f"/fiscal/deducciones/{selected_year}")
            
            if detalle_response and detalle_response.status_code == 200:
                detalle = detalle_response.json()
                breakdown = detalle.get('breakdown', {})
                
                for category, cfdis in breakdown.items():
                    if cfdis:
                        with st.expander(f"{category.replace('_', ' ').title()} ({len(cfdis)} CFDIs)"):
                            for cfdi in cfdis:
                                st.write(f"**{cfdi['emisor']}** - ${cfdi['total']:,.2f}")
                                st.caption(f"Fecha: {cfdi['fecha']} | UUID: {cfdi['uuid'][:8]}...")
    
    with tab3:
        st.subheader(f"Resumen Anual {selected_year}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💰 Total Ingresos", f"${ingresos.get('total', 0):,.2f} MXN")
        
        with col2:
            st.metric("📉 Total Deducciones", f"${deducciones.get('total', 0):,.2f} MXN")
        
        with col3:
            st.metric("💵 Base Gravable", f"${data.get('base_gravable', 0):,.2f} MXN")
        
        st.divider()
        
        # Impuestos
        st.subheader("🏛️ Impuestos")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("💳 ISR Retenido", f"${impuestos.get('isr_retenido', 0):,.2f} MXN")
        
        with col2:
            st.metric("💳 ISR Pagado", f"${impuestos.get('isr_pagado', 0):,.2f} MXN")
        
        st.divider()
        
        # Stats
        st.info(f"📊 Calculado desde {data.get('total_cfdis', 0)} CFDIs")
        
        if data.get('ultimo_calculo'):
            st.caption(f"Último cálculo: {data['ultimo_calculo']}")
        
        if st.button("🔄 Recalcular"):
            recalc_response = api_request(f"/fiscal/prestaciones/{selected_year}?recalcular=true")
            if recalc_response and recalc_response.status_code == 200:
                st.success("✅ Prestaciones recalculadas")
                st.rerun()
        
        st.divider()
        
        st.subheader("📋 Declaraciones Presentadas")
        st.info("🔄 Conecta tus credenciales SAT para ver el historial de declaraciones")
        
        # Placeholder for declarations history
        declarations = []
        if declarations:
            st.dataframe(declarations, use_container_width=True)
        else:
            st.warning("No hay declaraciones registradas para este año")
        
        st.divider()
        
        st.subheader("📥 Descargar Constancia de Situación Fiscal")
        if st.button("📄 Solicitar Constancia", use_container_width=True):
            st.info("🚧 Esta función requerirá tus credenciales SAT configuradas")


def show_cfdis():
    """CFDI (Factura Electrónica) management"""
    st.header("🧾 Facturas Electrónicas (CFDIs)")
    
    # Upload section
    with st.expander("📤 Subir CFDIs Manualmente"):
        st.info("Sube archivos XML de CFDIs que tengas guardados")
        
        uploaded_files = st.file_uploader(
            "Selecciona archivos XML de CFDIs",
            type=['xml'],
            accept_multiple_files=True,
            help="Puedes subir múltiples archivos a la vez"
        )
        
        if uploaded_files and st.button("📥 Procesar CFDIs"):
            success_count = 0
            error_count = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Procesando {uploaded_file.name}...")
                
                # Upload file
                files = {"file": (uploaded_file.name, uploaded_file, "application/xml")}
                upload_response = api_request("/cfdis/upload", "POST", files=files)
                
                if upload_response and upload_response.status_code in [200, 201]:
                    success_count += 1
                elif upload_response and upload_response.status_code == 409:
                    st.warning(f"⚠️ {uploaded_file.name}: Ya existe")
                else:
                    error_count += 1
                    if upload_response:
                        error_detail = upload_response.json().get('detail', 'Error desconocido')
                        st.error(f"❌ {uploaded_file.name}: {error_detail}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            status_text.empty()
            progress_bar.empty()
            
            if success_count > 0:
                st.success(f"✅ {success_count} CFDIs procesados exitosamente")
                st.rerun()
            
            if error_count > 0:
                st.error(f"❌ {error_count} CFDIs con errores")
    
    st.divider()
    
    # Get statistics
    stats_response = api_request("/cfdis/stats")
    
    if stats_response and stats_response.status_code == 200:
        stats = stats_response.json()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📄 Total CFDIs", stats.get("total_cfdis", 0))
        
        with col2:
            st.metric("💰 Total Ingresos", f"${stats.get('total_ingresos', 0):,.2f}")
        
        with col3:
            st.metric("📉 Total Egresos", f"${stats.get('total_egresos', 0):,.2f}")
        
        with col4:
            st.metric("📋 Nóminas", stats.get("total_nominas", 0))
    
    st.divider()
    
    # Filters
    st.subheader("🔍 Filtrar CFDIs")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        year_filter = st.selectbox("Año", [None] + list(range(datetime.now().year, datetime.now().year - 10, -1)))
    
    with col2:
        month_filter = st.selectbox("Mes", [None] + list(range(1, 13))) if year_filter else None
    
    with col3:
        tipo_filter = st.selectbox("Tipo", [None, "I - Ingreso", "E - Egreso", "N - Nómina"])
    
    # Build query params
    params = {}
    if year_filter:
        params['year'] = year_filter
    if month_filter:
        params['month'] = month_filter
    if tipo_filter:
        params['tipo'] = tipo_filter.split(" - ")[0]
    
    # Build query string
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    endpoint = f"/cfdis/?{query_string}" if query_string else "/cfdis/"
    
    # Get CFDIs list
    cfdis_response = api_request(endpoint)
    
    if cfdis_response and cfdis_response.status_code == 200:
        data = cfdis_response.json()
        cfdis = data.get('cfdis', [])
        total = data.get('total', 0)
        
        st.info(f"📊 Mostrando {len(cfdis)} de {total} CFDIs")
        
        if cfdis:
            for cfdi in cfdis:
                with st.expander(
                    f"🧾 {cfdi['emisor']['nombre']} - ${cfdi['montos']['total']:,.2f} MXN - {cfdi['fecha_emision'][:10]}"
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Emisor**")
                        st.write(f"RFC: {cfdi['emisor']['rfc']}")
                        st.write(f"Nombre: {cfdi['emisor']['nombre']}")
                        
                        st.write("**Montos**")
                        st.write(f"Subtotal: ${cfdi['montos']['subtotal']:,.2f}")
                        st.write(f"IVA: ${cfdi['montos']['iva']:,.2f}")
                        st.write(f"**Total: ${cfdi['montos']['total']:,.2f}**")
                    
                    with col2:
                        st.write("**Detalles**")
                        st.write(f"UUID: {cfdi['uuid']}")
                        st.write(f"Serie/Folio: {cfdi.get('serie', 'N/A')}/{cfdi.get('folio', 'N/A')}")
                        st.write(f"Tipo: {cfdi['tipo_comprobante']}")
                        st.write(f"Fecha: {cfdi['fecha_emision']}")
                        
                        if cfdi.get('es_deducible'):
                            st.success("✅ Deducible")
                    
                    # Conceptos
                    if cfdi.get('conceptos'):
                        st.write("**Conceptos:**")
                        for concepto in cfdi['conceptos']:
                            st.caption(f"• {concepto.get('descripcion', 'N/A')} - ${concepto.get('importe', 0):,.2f}")
        else:
            st.info("No hay CFDIs con los filtros seleccionados")
    else:
        st.warning("⚠️ No se pudieron cargar los CFDIs")


def main():
    """Main application"""
    st.set_page_config(
        page_title="Gestor Fiscal SAT",
        page_icon="🏛️",
        layout="wide"
    )
    
    # Check if logged in
    if st.session_state.token is None:
        login_page()
    else:
        dashboard_page()
    
    # Show connection status indicator at the end
    show_connection_status()


if __name__ == "__main__":
    main()
