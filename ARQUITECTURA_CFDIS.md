# 🏗️ Arquitectura del Sistema - Integración SAT

## 📊 Diagrama General

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FRONTEND - Streamlit                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Dashboard con 5 Pestañas:                                    │  │
│  │  1. Dashboard (Resumen)                                      │  │
│  │  2. Perfil Fiscal                                            │  │
│  │  3. Documentos                                               │  │
│  │  4. 🧾 CFDIs ←── NUEVO MÓDULO                               │  │
│  │  5. 🔐 Credenciales SAT                                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND - FastAPI                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ API Endpoints (/api/v1/):                                  │   │
│  │                                                             │   │
│  │ Authentication:                                             │   │
│  │  • POST /auth/register                                     │   │
│  │  • POST /auth/login                                        │   │
│  │                                                             │   │
│  │ Credentials:                                                │   │
│  │  • GET /credentials/sat                                    │   │
│  │  • POST /credentials/sat                                   │   │
│  │  • PUT /credentials/sat                                    │   │
│  │  • DELETE /credentials/sat                                 │   │
│  │                                                             │   │
│  │ CFDIs: ←── NUEVO MÓDULO                                    │   │
│  │  • GET /cfdi/list (con filtros)                            │   │
│  │  • POST /cfdi/sync (sync con SAT)                          │   │
│  │  • GET /cfdi/{uuid}/xml                                    │   │
│  │  • GET /cfdi/{uuid}/pdf                                    │   │
│  │  • GET /cfdi/{uuid}/details                                │   │
│  │  • GET /cfdi/statistics                                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│              AUTOMATION - SAT Portal Integration                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ SATAutomation (Selenium)                                   │   │
│  │  • login_sat(rfc, password)                                │   │
│  │  • get_cfdis(rfc, password, dates)                         │   │
│  │  • _extract_cfdi_table()                                   │   │
│  │                                                             │   │
│  │ Portal URLs:                                                │   │
│  │  • Login: https://www.sat.gob.mx/usuarios/portal/portal   │   │
│  │  • CFDIs: https://www.sat.gob.mx/aplicacion/descargamasiva│   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    DATABASE - PostgreSQL                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Tables:                                                    │   │
│  │  • users                                                   │   │
│  │  • sat_credentials (con contraseña cifrada)               │   │
│  │  • fiscal_profiles                                         │   │
│  │  • documents                                               │   │
│  │  • notifications                                           │   │
│  │  • audit_logs                                              │   │
│  │  • cfdi_cache (próximamente)                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔄 Flujo de Datos - Descarga de CFDIs

```
Usuario (Streamlit)
    │
    ├─→ Click en pestaña "🧾 CFDIs"
    │
    └─→ Frontend: show_cfdis()
         │
         ├─→ Valida credenciales configuradas
         │   GET /api/v1/credentials/sat
         │
         ├─→ Muestra filtros
         │   (Tipo, Estado, Fecha)
         │
         └─→ Usuario selecciona filtros
             │
             └─→ Llama API
                 GET /api/v1/cfdi/list?cfdi_type=emitido&...
                     │
                     └─→ Backend: list_cfdis()
                         │
                         ├─→ Verifica caché
                         │   Si existe → retorna
                         │
                         ├─→ Obtiene credenciales SAT
                         │   SELECT * FROM sat_credentials
                         │
                         ├─→ Desencripta password
                         │   decrypt_data(encrypted_password)
                         │
                         ├─→ Llama SATAutomation
                         │   fetch_cfdis_from_sat()
                         │       │
                         │       ├─→ Selenium abre navegador
                         │       │
                         │       ├─→ login_sat(rfc, password)
                         │       │   • Abre portal del SAT
                         │       │   • Completa formulario de login
                         │       │   • Espera confirmación
                         │       │
                         │       ├─→ get_cfdis()
                         │       │   • Navega a descarga masiva
                         │       │   • Selecciona tipo (emitido/recibido)
                         │       │   • Establece fechas
                         │       │   • Busca en SAT
                         │       │   • Extrae datos de tabla
                         │       │
                         │       └─→ Cierra navegador
                         │
                         ├─→ Cachea resultados
                         │   _cfdi_cache[cache_key] = cfdis
                         │
                         └─→ Retorna lista de CFDIs
                             [
                               {uuid, tipo, fecha, rfc_emisor, ...},
                               ...
                             ]

Usuario (Frontend)
    │
    └─→ Renderiza tabla/vista expandida
        │
        ├─→ Estadísticas
        │   GET /api/v1/cfdi/statistics
        │
        ├─→ Filtros funcionales
        │
        └─→ Botones de descarga
            │
            ├─→ Click "Descargar XML"
            │   GET /api/v1/cfdi/{uuid}/xml
            │   → Descarga archivo XML
            │
            └─→ Click "Descargar PDF"
                GET /api/v1/cfdi/{uuid}/pdf
                → Descarga archivo PDF (reportlab)
```

## 🔐 Flujo de Seguridad

```
1. Usuario ingresa RFC + Contraseña
   ↓
2. Frontend envía a Backend (HTTPS)
   POST /api/v1/credentials/sat
   ↓
3. Backend valida JWT
   ↓
4. Backend encripta contraseña
   Fernet.encrypt(password + ENCRYPTION_KEY)
   ↓
5. Backend almacena en DB
   INSERT INTO sat_credentials (user_id, rfc, encrypted_password)
   ↓
6. Cuando se necesitan CFDIs:
   ├─→ Backend obtiene datos cifrados
   ├─→ Desencripta en MEMORIA (no disco)
   ├─→ Pasa a SATAutomation
   ├─→ SATAutomation usa credenciales
   ├─→ Cierra navegador (logout automático)
   └─→ Credenciales ya no están en memoria
```

## 💾 Estructura de Caché

```python
_cfdi_cache = {
    # Clave: "{user_id}_{cfdi_type}_{start_date}_{end_date}"
    "1_emitido_2025-01-01_2025-12-31": [
        {
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "tipo": "ingreso",
            "fecha": "2025-11-15T10:30:00",
            "rfc_emisor": "AAA010101AAA",
            "nombre_emisor": "Empresa A",
            "rfc_receptor": "BBB020202BBB",
            "nombre_receptor": "Empresa B",
            "subtotal": 1000.00,
            "total": 1160.00,
            "moneda": "MXN",
            "status": "vigente",
            "xml_url": "/api/v1/cfdi/{uuid}/xml",
            "pdf_url": "/api/v1/cfdi/{uuid}/pdf"
        },
        ...más CFDIs...
    ],
    "1_recibido_2025-01-01_2025-12-31": [
        ...
    ]
}
```

## 📁 Estructura de Archivos

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── credentials.py
│   │           ├── cfdi.py ←── NUEVO
│   │           └── ...
│   ├── automation/
│   │   ├── ocr_service.py
│   │   ├── rfc_validator.py
│   │   └── sat_automation.py ←── ACTUALIZADO
│   ├── core/
│   │   ├── config.py ←── ACTUALIZADO
│   │   ├── database.py
│   │   ├── security.py
│   │   └── ...
│   ├── models/
│   │   ├── user.py
│   │   ├── sat_credentials.py
│   │   └── ...
│   ├── schemas/
│   │   ├── sat.py
│   │   └── ...
│   └── main.py
├── requirements.txt ←── ACTUALIZADO (+ reportlab)
└── ...

frontend/
├── streamlit_app.py ←── ACTUALIZADO (+ show_cfdis)
└── ...

docs/
├── INTEGRACION_SAT.md ←── NUEVO
├── GUIA_USO_CFDIS.md ←── NUEVO
└── ARQUITECTURA.md
```

## 🔌 Endpoints Completos

### CFDIs

| Método | Endpoint | Descripción | Parámetros |
|--------|----------|-------------|-----------|
| GET | `/cfdi/list` | Lista CFDIs del usuario | `cfdi_type`, `start_date`, `end_date`, `status`, `use_cache` |
| POST | `/cfdi/sync` | Sincroniza con SAT | - |
| GET | `/cfdi/{uuid}/xml` | Descarga XML | - |
| GET | `/cfdi/{uuid}/pdf` | Descarga PDF | - |
| GET | `/cfdi/{uuid}/details` | Detalles CFDI | - |
| GET | `/cfdi/statistics` | Estadísticas | `year` |

### Credenciales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/credentials/sat` | Estado de credenciales |
| POST | `/credentials/sat` | Guardar credenciales |
| PUT | `/credentials/sat` | Actualizar credenciales |
| DELETE | `/credentials/sat` | Eliminar credenciales |
| POST | `/credentials/efirma/upload` | Subir certificados |
| POST | `/credentials/test-connection` | Probar conexión SAT |

## ⚙️ Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web asincrónico
- **SQLAlchemy**: ORM para BD
- **Pydantic**: Validación de datos
- **Selenium**: Automatización del navegador
- **Reportlab**: Generación de PDFs
- **Cryptography (Fernet)**: Encriptación AES-256

### Frontend
- **Streamlit**: Interface web interactiva
- **Pandas**: Manejo de dataframes
- **Requests**: Cliente HTTP

### Base de Datos
- **PostgreSQL**: BD principal
- **Redis**: Caché en memoria

### Infraestructura
- **Docker**: Containerización
- **Docker Compose**: Orquestación de servicios

## 🚀 Mejoras Futuras

1. **API Oficial del SAT**
   - Cuando SAT publique API RESTful oficial
   - Reemplazar Selenium con HTTP client

2. **Almacenamiento de CFDIs**
   - Nueva tabla `cfdi_data` en BD
   - Búsqueda histórica sin sincronizar

3. **Descarga Múltiple**
   - Descargar varios CFDIs en ZIP
   - Descarga en lote

4. **Reportes**
   - Excel/CSV con todos los CFDIs
   - Reportes fiscales personalizados

5. **Validación de Firmas**
   - Verificar firma digital del CFDI
   - Validar timestamps

6. **OCR**
   - Procesar facturas en papel
   - Integración automática

7. **Notificaciones**
   - Alertas de nuevos CFDIs
   - Resumen diario/semanal

8. **Análisis**
   - Dashboard de análisis fiscal
   - Proyecciones de impuestos

## 📈 Rendimiento Esperado

### Tiempos de Respuesta
- Login SAT: 5-10 segundos
- Descarga de CFDIs: 1-3 minutos (depende del SAT)
- Caché local: < 100ms

### Escalabilidad
- Usuarios simultáneos: 10-50 (sin proxy)
- CFDIs en caché: Ilimitado (en RAM)
- Tiempo de caché: Session-based

### Limitaciones
- Portal SAT puede rechazar múltiples conexiones simultáneas
- Sesiones del navegador se cierran después de cada uso
- Requiere conexión a internet estable

## 🔍 Monitoreo

### Logs
Todos los eventos se registran:
```
[INFO] Attempting SAT login for RFC: AAA010101AAA
[INFO] SAT login successful
[INFO] Fetching emitidos CFDIs
[INFO] Successfully extracted 42 CFDIs
[ERROR] Error downloading PDF: [reason]
```

### Métricas
- Cantidad de logins exitosos/fallidos
- Tiempo promedio de descarga
- Cantidad de CFDIs por usuario
- Errores de conexión

---

**Última actualización**: Diciembre 3, 2025
