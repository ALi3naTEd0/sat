# Integración con Portal del SAT

## 📋 Descripción General

Este documento explica cómo funciona la integración automática con el portal del SAT para descargar CFDIs (Comprobantes Fiscales Digitales por Internet).

## 🔧 Arquitectura de Integración

### Componentes Principales

1. **`app/automation/sat_automation.py`** - Módulo de automatización
   - Usa Selenium para automatizar el navegador web
   - Se conecta al portal del SAT en: `https://www.sat.gob.mx`
   - Descarga masiva de CFDIs desde: `https://www.sat.gob.mx/aplicacion/descargamasiva/form.html`

2. **`app/api/v1/endpoints/cfdi.py`** - Endpoints API
   - `GET /api/v1/cfdi/list` - Lista CFDIs del usuario
   - `POST /api/v1/cfdi/sync` - Sincroniza CFDIs desde SAT
   - `GET /api/v1/cfdi/{uuid}/xml` - Descarga XML del CFDI
   - `GET /api/v1/cfdi/{uuid}/pdf` - Descarga PDF del CFDI

3. **`frontend/streamlit_app.py`** - Interface de usuario
   - Sección "🧾 CFDIs" con tabla de facturas
   - Filtros por tipo (emitido/recibido) y estado
   - Botones de descarga de XML/PDF

## 🔑 Flujo de Autenticación

```
1. Usuario configura credenciales SAT (RFC + Contraseña)
   ↓
2. Credenciales se cifran con Fernet (AES-256)
   ↓
3. Se almacenan en BD en tabla `sat_credentials`
   ↓
4. Al descargar CFDIs, se desencriptan las credenciales
   ↓
5. Selenium se conecta al SAT usando RFC + Contraseña
   ↓
6. Se extrae información de CFDIs de las tablas del portal
```

## 🚀 Proceso de Descarga de CFDIs

### Paso 1: Login en SAT
```python
# Se accede a: https://www.sat.gob.mx/usuarios/portal/portal.html
1. Completa campo RFC (sin homoclave)
2. Completa campo Contraseña
3. Hace clic en botón "Enviar"
4. Espera confirmación de login exitoso
```

### Paso 2: Descarga Masiva
```python
# Se accede a: https://www.sat.gob.mx/aplicacion/descargamasiva/form.html
1. Selecciona tipo de CFDI:
   - "emitidos" (facturas que emitió)
   - "recibidos" (facturas que recibió)
2. Establece rango de fechas (formato DD/MM/YYYY)
3. Hace clic en "Buscar"
4. Extrae datos de la tabla de resultados
```

### Paso 3: Extracción de Datos
```python
# De cada fila de la tabla se extrae:
- uuid: ID único del CFDI
- fecha: Fecha del comprobante
- rfc_emisor: RFC de quien emite
- nombre_emisor: Nombre de la empresa que emite
- rfc_receptor: RFC de quien recibe
- nombre_receptor: Nombre de quien recibe
- total: Monto total del CFDI
- status: "vigente" o "cancelado"
```

## 💾 Caché de CFDIs

Los CFDIs descargados se cachean en memoria con la siguiente estructura:
```python
_cfdi_cache = {
    "user_id_tipo_fecha_inicio_fecha_fin": [
        {
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "tipo": "ingreso",
            "fecha": "2025-11-15",
            ...
        }
    ]
}
```

- La caché se limpia cuando se sincroniza (`/api/v1/cfdi/sync`)
- Se puede forzar nuevas descargas con parámetro `use_cache=false`

## 🛡️ Seguridad

### Encriptación de Credenciales
- RFC: Se almacena en texto plano (es público)
- Contraseña: Se encripta con Fernet (AES-256)
- Clave de encriptación: Viene de `app.core.security.ENCRYPTION_KEY`

### Protección de Sesión
- Cada usuario solo ve sus propios CFDIs
- Se valida con JWT en cada request
- Las credenciales SAT solo se desencriptan en memoria

## ⚙️ Configuración

En archivo `.env`:

```env
# SAT Integration
SAT_BASE_URL="https://www.sat.gob.mx"
SAT_PORTAL_URL="https://portalcfdi.facturaelectronica.sat.gob.mx"
SAT_TIMEOUT_SECONDS=30
SAT_MAX_RETRIES=3

# Automation
HEADLESS_BROWSER=true
SELENIUM_TIMEOUT=30
```

## 🔍 Manejo de Errores

### Errores Comunes

1. **Credenciales Inválidas**
   - Response: `{"success": false, "message": "Credenciales inválidas o fallo en login"}`
   - Solución: Validar RFC y contraseña en portal SAT

2. **Timeout de Conexión**
   - Causa: Portal SAT lento o no disponible
   - Response: `{"success": false, "message": "Tiempo de espera agotado"}`
   - Solución: Reintentar o esperar a que SAT responda

3. **Sin Credenciales Configuradas**
   - Response: Se retorna data de demostración
   - Solución: Configurar credenciales en pestaña "🔐 Credenciales SAT"

4. **Sesión Expirada**
   - El navegador se cierra después de cada operación
   - Se crea una nueva sesión en siguiente request

## 📊 Campos de Respuesta CFDI

```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "tipo": "ingreso",                          // ingreso, egreso, traslado
  "fecha": "2025-11-15T10:30:00",
  "rfc_emisor": "AAA010101AAA",
  "nombre_emisor": "Empresa Ejemplo S.A.",
  "rfc_receptor": "BBB020202BBB",
  "nombre_receptor": "Cliente",
  "subtotal": 1000.00,
  "total": 1160.00,                           // Incluye impuestos
  "moneda": "MXN",
  "status": "vigente",                        // vigente, cancelado
  "xml_url": "/api/v1/cfdi/{uuid}/xml",
  "pdf_url": "/api/v1/cfdi/{uuid}/pdf"
}
```

## 🔄 Endpoints Disponibles

### Listar CFDIs
```
GET /api/v1/cfdi/list?cfdi_type=emitido&start_date=2025-01-01&end_date=2025-12-31&use_cache=true
```
Respuesta: Lista de objetos CFDI

### Sincronizar con SAT
```
POST /api/v1/cfdi/sync
```
Respuesta:
```json
{
  "success": true,
  "message": "Sincronización completada con éxito",
  "cfdis_imported": 42,
  "last_sync": "2025-12-03T12:34:56.789Z"
}
```

### Descargar XML
```
GET /api/v1/cfdi/{uuid}/xml
```
Respuesta: Archivo XML del CFDI (Content-Type: application/xml)

### Descargar PDF
```
GET /api/v1/cfdi/{uuid}/pdf
```
Respuesta: Archivo PDF del CFDI (Content-Type: application/pdf)

### Obtener Detalles
```
GET /api/v1/cfdi/{uuid}/details
```
Respuesta: JSON con detalles completos del CFDI

### Estadísticas
```
GET /api/v1/cfdi/statistics?year=2025
```
Respuesta:
```json
{
  "total_emitidos": 5,
  "total_recibidos": 3,
  "monto_total_emitido": 45000.00,
  "monto_total_recibido": 12000.00,
  "iva_trasladado": 7200.00,
  "iva_retenido": 300.00
}
```

## 🐛 Debugging

### Logs
Los logs están disponibles en el archivo de logging del backend:
```
[INFO] Attempting SAT login for RFC: AAA010101AAA
[INFO] SAT login successful for RFC: AAA010101AAA
[INFO] Fetching emitidos CFDIs from 2025-01-01 to 2025-12-31
[INFO] Successfully extracted 42 CFDIs from table
```

### Modo Debug
Para ver la sesión del navegador sin headless:
```python
# En app/automation/sat_automation.py
# Cambiar: HEADLESS_BROWSER=false en .env
chrome_options.add_argument('--headless=new')  # Comentar esta línea
```

## 🔮 Mejoras Futuras

1. **API Oficial del SAT**: Cuando SAT publique API oficial, reemplazar Selenium
2. **Descarga de Archivos**: Descargar archivos XML/PDF directamente del SAT
3. **Validación de Firma**: Validar firma digital de CFDIs
4. **Almacenamiento Local**: Guardar CFDIs en BD para búsqueda histórica
5. **OCR de Facturas**: Procesar imágenes de facturas en papel
6. **Alertas**: Notificar nuevos CFDIs automáticamente

## 📝 Notas Importantes

- El portal del SAT puede cambiar su estructura HTML, lo que requeriría actualizar los selectores CSS/XPath
- Se recomienda implementar reintentos con backoff exponencial para resiliencia
- Las credenciales deben tener acceso habilitado en el portal del SAT
- El RFC debe ser válido (13 caracteres sin homoclave) - el SAT lo agrega automáticamente
- Las contraseñas se cachean en memoria de Selenium, no se persisten

## 🚨 Troubleshooting

### "Connection refused"
- Verificar que conexión a internet sea estable
- El portal SAT puede estar en mantenimiento

### "Credenciales inválidas"
- Validar que el RFC + contraseña sean correctos
- Acceder manualmente al portal SAT para confirmar

### "Timeout"
- Aumentar `SELENIUM_TIMEOUT` en .env
- Reintentar la operación

### "No se encuentran CFDIs"
- Verificar que existan CFDIs en el período seleccionado
- Intentar con rango de fechas más amplio
