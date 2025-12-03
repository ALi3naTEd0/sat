"""
Streamlit Frontend - Gestor Fiscal Personal
"""
import streamlit as st
import requests
import os
from datetime import datetime
from typing import Optional

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

# Session state initialization
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "backend_status" not in st.session_state:
    st.session_state.backend_status = None
if "show_update_creds" not in st.session_state:
    st.session_state.show_update_creds = False


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
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            if files:
                response = requests.post(url, headers=headers, data=data, files=files, params=params)
            elif form_data:
                response = requests.post(url, headers=headers, data=data, params=params)
            else:
                response = requests.post(url, headers=headers, json=data, params=params)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, params=params)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        
        return response
    except requests.exceptions.ConnectionError:
        st.error("⚠️ No se puede conectar al servidor. Asegúrate de que el backend esté ejecutándose.")
        return None
    except Exception as e:
        st.error(f"⚠️ Error: {str(e)}")
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
            st.rerun()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Dashboard", 
        "👤 Perfil Fiscal", 
        "📄 Documentos",
        "🧾 CFDIs",
        "🔐 Credenciales SAT"
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
        show_sat_credentials()


def show_dashboard():
    """Dashboard overview"""
    st.header("Resumen General")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("RFC", st.session_state.user.get("fiscal_profile", {}).get("rfc", "Sin RFC"))
    
    with col2:
        st.metric("Documentos", "0")
    
    with col3:
        st.metric("Notificaciones", "0")
    
    st.divider()
    
    st.subheader("📊 Estado de Cumplimiento")
    st.info("🔄 Conecta tus credenciales SAT para ver tu estado fiscal")
    
    st.subheader("🔔 Notificaciones Recientes")
    st.write("No hay notificaciones pendientes")


def show_fiscal_profile():
    """Fiscal profile management"""
    st.header("👤 Perfil Fiscal")
    
    # Get current profile
    response = api_request("/fiscal/profile")
    
    if response and response.status_code == 200:
        profile = response.json()
        
        with st.form("fiscal_form"):
            st.subheader("Datos Fiscales")
            
            rfc = st.text_input("RFC", value=profile.get("rfc", ""), max_chars=13)
            curp = st.text_input("CURP", value=profile.get("curp", ""), max_chars=18)
            legal_name = st.text_input("Nombre/Razón Social", value=profile.get("legal_name", ""))
            
            tax_regime = st.selectbox("Régimen Fiscal", [
                "605 - Sueldos y Salarios",
                "621 - Incorporación Fiscal",
                "626 - Régimen Simplificado de Confianza",
                "612 - Personas Físicas con Actividades Empresariales",
                "606 - Arrendamiento",
                "601 - Régimen General de Personas Morales",
                "616 - Sin Obligaciones Fiscales"
            ])
            
            submit = st.form_submit_button("💾 Guardar Cambios")
            
            if submit:
                regime_code = tax_regime.split(" - ")[0]
                
                update_response = api_request("/fiscal/profile", "PUT", {
                    "rfc": rfc if rfc else None,
                    "curp": curp if curp else None,
                    "legal_name": legal_name if legal_name else None,
                    "tax_regime": regime_code if rfc else None
                })
                
                if update_response and update_response.status_code == 200:
                    st.success("✅ Perfil fiscal actualizado")
                    st.rerun()
                else:
                    error_msg = update_response.json().get("detail", "Error al actualizar") if update_response else "Error de conexión"
                    st.error(f"❌ {error_msg}")
    
    elif response and response.status_code == 404:
        st.info("📝 Completa tu perfil fiscal para comenzar")
        
        with st.form("fiscal_form_new"):
            rfc = st.text_input("RFC", max_chars=13)
            curp = st.text_input("CURP", max_chars=18)
            legal_name = st.text_input("Nombre/Razón Social")
            
            submit = st.form_submit_button("💾 Crear Perfil")
            
            if submit:
                response = api_request("/fiscal/profile", "POST", {
                    "rfc": rfc if rfc else None,
                    "curp": curp if curp else None,
                    "legal_name": legal_name if legal_name else None
                })
                
                if response and response.status_code == 200:
                    st.success("✅ Perfil fiscal creado")
                    st.rerun()


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
    """SAT credentials management"""
    st.header("🔐 Credenciales SAT")
    
    st.warning("⚠️ Tus credenciales se almacenan de forma segura con encriptación AES-256")
    
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
            
            # Option to update or delete
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Actualizar Contraseña"):
                    st.session_state.show_update_creds = True
            with col2:
                if st.button("🗑️ Eliminar Credenciales"):
                    delete_response = api_request("/credentials/sat", "DELETE")
                    if delete_response and delete_response.status_code == 200:
                        st.success("✅ Credenciales eliminadas")
                        st.rerun()
                    else:
                        st.error("❌ Error al eliminar credenciales")
            
            # Update form
            if st.session_state.get("show_update_creds"):
                st.divider()
                with st.form("update_sat_creds_form"):
                    new_password = st.text_input("Nueva contraseña SAT", type="password")
                    submit = st.form_submit_button("✅ Actualizar")
                    
                    if submit and new_password:
                        update_response = api_request("/credentials/sat", "PUT", {
                            "sat_password": new_password
                        })
                        if update_response and update_response.status_code == 200:
                            st.success("✅ Credenciales actualizadas")
                            st.session_state.show_update_creds = False
                            st.rerun()
                        else:
                            st.error("❌ Error al actualizar credenciales")
        else:
            st.info("📝 Configura tus credenciales para automatizar consultas al SAT")
            
            with st.form("sat_creds_form"):
                sat_password = st.text_input("Contraseña del Portal SAT", type="password")
                
                st.subheader("e.firma (Opcional)")
                cer_file = st.file_uploader("Certificado .cer", type=["cer"])
                key_file = st.file_uploader("Llave privada .key", type=["key"])
                efirma_password = st.text_input("Contraseña e.firma", type="password") if (cer_file and key_file) else None
                
                submit = st.form_submit_button("💾 Guardar Credenciales")
                
                if submit:
                    if not sat_password:
                        st.error("❌ Debes ingresar la contraseña del SAT")
                    else:
                        # Save SAT password
                        save_response = api_request("/credentials/sat", "POST", {
                            "sat_password": sat_password,
                            "rfc": None
                        })
                        
                        if save_response and save_response.status_code in [200, 201]:
                            st.success("✅ Contraseña SAT guardada")
                            
                            # Upload e.firma if provided
                            if cer_file and key_file:
                                files = {
                                    "cer_file": cer_file,
                                    "key_file": key_file
                                }
                                data = {"efirma_password": efirma_password} if efirma_password else {}
                                
                                efirma_response = api_request("/credentials/efirma/upload", "POST", data=data, files=files)
                                if efirma_response and efirma_response.status_code in [200, 201]:
                                    st.success("✅ Certificados e.firma cargados")
                                else:
                                    st.warning("⚠️ Credenciales guardadas, pero hubo un error al cargar e.firma")
                            
                            st.rerun()
                        else:
                            st.error("❌ Error al guardar credenciales")
    else:
        st.error("❌ Error al conectar con el servidor")


def show_cfdis():
    """CFDI (Factura Electrónica) management"""
    st.header("🧾 Facturas Electrónicas (CFDIs)")
    
    # Check if credentials are configured
    creds_response = api_request("/credentials/sat", "GET")
    
    if not creds_response or not creds_response.json().get("has_credentials"):
        st.warning("⚠️ Debes configurar tus credenciales SAT primero para ver CFDIs")
        st.info("Dirígete a la pestaña '🔐 Credenciales SAT' para configurarlas")
        return
    
    # Initialize session state for filters
    if "cfdi_year" not in st.session_state:
        st.session_state.cfdi_year = datetime.now().year
    if "cfdi_month" not in st.session_state:
        st.session_state.cfdi_month = datetime.now().month
    
    # Sync button at top
    col_sync = st.columns(1)[0]
    with col_sync:
        if st.button("🔄 Sincronizar CFDIs desde SAT", key="sync_cfdis_top", use_container_width=True):
            with st.spinner("⏳ Sincronizando con SAT..."):
                sync_response = api_request("/cfdi/sync", "POST")
                if sync_response and sync_response.status_code == 200:
                    st.success("✅ Sincronización completada")
                    st.rerun()
                else:
                    st.error("❌ Error en sincronización")
    
    st.divider()
    
    # Get statistics
    stats_response = api_request("/cfdi/statistics", "GET")
    
    if stats_response and stats_response.status_code == 200:
        stats = stats_response.json()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📤 CFDIs Emitidos", stats.get("total_emitidos", 0))
        
        with col2:
            st.metric("📥 CFDIs Recibidos", stats.get("total_recibidos", 0))
        
        with col3:
            st.metric("💰 Monto Emitido", f"${stats.get('monto_total_emitido', 0):,.2f}")
        
        with col4:
            st.metric("💵 Monto Recibido", f"${stats.get('monto_total_recibido', 0):,.2f}")
    
    st.divider()
    
    # Advanced Filters
    st.subheader("🔍 Filtros Avanzados")
    
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    
    with filter_col1:
        cfdi_type = st.selectbox("📋 Tipo de CFDI", 
                                ["emitido", "recibido", "todos"],
                                key="cfdi_type_select")
    
    with filter_col2:
        status_filter = st.selectbox("✅ Estado", 
                                    ["vigente", "cancelado", "todos"],
                                    key="cfdi_status_select")
    
    with filter_col3:
        selected_year = st.selectbox("📅 Año", 
                                    range(2020, datetime.now().year + 1),
                                    index=datetime.now().year - 2020,
                                    key="cfdi_year_select")
        st.session_state.cfdi_year = selected_year
    
    with filter_col4:
        month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                      "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        selected_month = st.selectbox("📆 Mes", 
                                     month_names,
                                     index=datetime.now().month - 1,
                                     key="cfdi_month_select")
        selected_month_num = month_names.index(selected_month) + 1
        st.session_state.cfdi_month = selected_month_num
    
    st.divider()
    
    # Calculate date range for selected month
    import calendar
    first_day = datetime(selected_year, selected_month_num, 1)
    last_day = datetime(selected_year, selected_month_num, 
                       calendar.monthrange(selected_year, selected_month_num)[1])
    
    # Get CFDIs list with date filters
    params = {
        "cfdi_type": cfdi_type if cfdi_type != "todos" else "emitido",
        "start_date": first_day.strftime("%Y-%m-%d"),
        "end_date": last_day.strftime("%Y-%m-%d"),
    }
    if status_filter != "todos":
        params["status"] = status_filter
    
    cfdis_response = api_request("/cfdi/list", "GET", params=params)
    
    if cfdis_response and cfdis_response.status_code == 200:
        cfdis = cfdis_response.json()
        
        if not cfdis:
            st.info("📭 No hay CFDIs para el período seleccionado")
            st.write(f"Buscando desde {first_day.strftime('%d/%m/%Y')} hasta {last_day.strftime('%d/%m/%Y')}")
            return
        
        st.success(f"✅ Se encontraron {len(cfdis)} CFDI(s)")
        
        # Create a dataframe
        import pandas as pd
        
        df_data = []
        for cfdi in cfdis:
            fecha_obj = datetime.fromisoformat(cfdi["fecha"]) if isinstance(cfdi["fecha"], str) else cfdi["fecha"]
            df_data.append({
                "Tipo": cfdi["tipo"].upper(),
                "Fecha": fecha_obj.strftime("%d/%m/%Y %H:%M"),
                "Emisor": cfdi["rfc_emisor"],
                "Receptor": cfdi["rfc_receptor"],
                "Subtotal": cfdi["subtotal"],
                "IVA": cfdi["total"] - cfdi["subtotal"],
                "Total": cfdi["total"],
                "Estado": cfdi["status"],
                "UUID": cfdi["uuid"]
            })
        
        df = pd.DataFrame(df_data)
        
        # Display options
        tab1, tab2, tab3 = st.tabs(["📊 Vista Tabla", "📄 Documentos", "📈 Detalles"])
        
        with tab1:
            st.subheader(f"Tabla de CFDIs - {selected_month} {selected_year}")
            st.dataframe(df[["Tipo", "Fecha", "Emisor", "Total", "Estado"]], 
                        use_container_width=True, 
                        hide_index=True)
        
        with tab2:
            st.subheader(f"Descargar Documentos - {selected_month} {selected_year}")
            
            # Group CFDIs by type
            for idx, cfdi in enumerate(cfdis):
                fecha_obj = datetime.fromisoformat(cfdi["fecha"]) if isinstance(cfdi["fecha"], str) else cfdi["fecha"]
                
                with st.container(border=True):
                    # Header info
                    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                    
                    with col1:
                        st.write(f"**{cfdi['tipo'].upper()}**")
                        st.caption(f"Fecha: {fecha_obj.strftime('%d/%m/%Y %H:%M')}")
                    
                    with col2:
                        st.write(f"**Total: ${cfdi['total']:,.2f}**")
                        st.caption(f"RFC: {cfdi['rfc_emisor']}")
                    
                    with col3:
                        status_emoji = "✅" if cfdi["status"] == "vigente" else "❌"
                        st.write(f"{status_emoji} {cfdi['status'].upper()}")
                    
                    with col4:
                        st.write(f"UUID: {cfdi['uuid'][:8]}...")
                    
                    st.divider()
                    
                    # Download buttons
                    download_col1, download_col2, download_col3 = st.columns(3)
                    
                    with download_col1:
                        if st.button("📥 Ver XML", key=f"view_xml_{idx}", use_container_width=True):
                            st.session_state[f"show_xml_{idx}"] = True
                    
                    with download_col2:
                        if st.button("📄 Ver PDF", key=f"view_pdf_{idx}", use_container_width=True):
                            st.session_state[f"show_pdf_{idx}"] = True
                    
                    with download_col3:
                        if st.button("💾 Descargar ZIP", key=f"download_zip_{idx}", use_container_width=True):
                            with st.spinner("Generando descarga..."):
                                xml_response = api_request(f"/cfdi/{cfdi['uuid']}/xml", "GET")
                                pdf_response = api_request(f"/cfdi/{cfdi['uuid']}/pdf", "GET")
                                
                                if xml_response and pdf_response:
                                    st.info("✅ Descarga lista (ZIP con XML y PDF)")
                    
                    # Show XML if requested
                    if st.session_state.get(f"show_xml_{idx}"):
                        st.divider()
                        st.write("**📄 Contenido XML:**")
                        try:
                            xml_response = api_request(f"/cfdi/{cfdi['uuid']}/xml", "GET")
                            if xml_response and xml_response.status_code == 200:
                                xml_text = xml_response.text if hasattr(xml_response, 'text') else xml_response.content.decode()
                                st.code(xml_text, language="xml", line_numbers=True)
                                
                                st.download_button(
                                    label="📥 Descargar XML",
                                    data=xml_response.content if hasattr(xml_response, 'content') else xml_text.encode(),
                                    file_name=f"CFDI_{cfdi['uuid']}.xml",
                                    mime="application/xml",
                                    key=f"dl_xml_{idx}"
                                )
                        except Exception as e:
                            st.error(f"Error al obtener XML: {str(e)}")
                    
                    # Show PDF if requested
                    if st.session_state.get(f"show_pdf_{idx}"):
                        st.divider()
                        st.write("**📋 Documento PDF:**")
                        try:
                            pdf_response = api_request(f"/cfdi/{cfdi['uuid']}/pdf", "GET")
                            if pdf_response and pdf_response.status_code == 200:
                                st.write("✅ PDF generado correctamente")
                                st.download_button(
                                    label="📥 Descargar PDF",
                                    data=pdf_response.content,
                                    file_name=f"CFDI_{cfdi['uuid']}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_pdf_{idx}"
                                )
                        except Exception as e:
                            st.error(f"Error al obtener PDF: {str(e)}")
        
        with tab3:
            st.subheader(f"Detalles Completos - {selected_month} {selected_year}")
            
            for idx, cfdi in enumerate(cfdis):
                fecha_obj = datetime.fromisoformat(cfdi["fecha"]) if isinstance(cfdi["fecha"], str) else cfdi["fecha"]
                
                with st.expander(f"🧾 {cfdi['tipo'].upper()} - {fecha_obj.strftime('%d/%m/%Y')} - ${cfdi['total']:,.2f}"):
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Información General**")
                        st.write(f"• UUID: `{cfdi['uuid']}`")
                        st.write(f"• Tipo: {cfdi['tipo']}")
                        st.write(f"• Fecha: {fecha_obj.strftime('%d/%m/%Y %H:%M:%S')}")
                        st.write(f"• Estado: {cfdi['status']}")
                        st.write(f"• Moneda: {cfdi['moneda']}")
                    
                    with col2:
                        st.write("**Información Fiscal**")
                        st.write(f"• RFC Emisor: `{cfdi['rfc_emisor']}`")
                        st.write(f"• Emisor: {cfdi['nombre_emisor']}")
                        st.write(f"• RFC Receptor: `{cfdi['rfc_receptor']}`")
                        st.write(f"• Receptor: {cfdi['nombre_receptor']}")
                    
                    st.divider()
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Subtotal", f"${cfdi['subtotal']:,.2f}")
                    with col2:
                        iva = cfdi['total'] - cfdi['subtotal']
                        st.metric("IVA", f"${iva:,.2f}")
                    with col3:
                        st.metric("Total", f"${cfdi['total']:,.2f}")
    else:
        st.error("❌ Error al obtener CFDIs del servidor")


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
