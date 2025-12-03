# 📚 Guía de Uso - Módulo de CFDIs

## 🎯 Objetivo

Este módulo permite a los usuarios descargar, ver y administrar sus Comprobantes Fiscales Digitales por Internet (CFDIs) directamente desde el portal del SAT integrado en la aplicación.

## 🚀 Inicio Rápido

### 1. Acceder a la Sección de CFDIs

1. Abre la aplicación en `http://localhost:8501`
2. Inicia sesión con tu usuario y contraseña
3. En el dashboard, haz clic en la pestaña **"🧾 CFDIs"**

### 2. Configurar Credenciales SAT (Primer Uso)

Si es tu primera vez usando el módulo de CFDIs:

1. Haz clic en la pestaña **"🔐 Credenciales SAT"** (última pestaña del dashboard)
2. Completa el formulario:
   - **RFC**: Tu RFC sin homoclave (13 caracteres)
   - **Contraseña**: Tu contraseña de acceso al SAT
3. Haz clic en **"💾 Guardar Credenciales"**

⚠️ **Nota importante**: Las credenciales se cifran antes de almacenarse. Solo se desencriptan cuando necesitas descargar CFDIs.

### 3. Ver Tus CFDIs

Una vez configuradas tus credenciales:

1. Ve a la pestaña **"🧾 CFDIs"**
2. Verás tres opciones en la parte superior:
   - **Tipo de CFDI**: Selecciona "emitido" (facturas que emitiste) o "recibido" (facturas que recibiste)
   - **Estado**: Filtra por "vigente" o "cancelado"
   - **Sincronizar**: Botón para actualizar desde el SAT en tiempo real

### 4. Descargar Archivos

El módulo ofrece dos formas de ver tus CFDIs:

#### Vista Tabla
- Tabla limpia y organizada
- Columnas: UUID, Tipo, Fecha, RFC Emisor, Total, Estado
- Fácil de ordenar y revisar rápidamente

#### Vista Expandida
- Haz clic en **"📈 Vista Expandida"**
- Cada CFDI se muestra en un panel expandible
- Información detallada:
  - RFC Emisor/Receptor
  - Nombres de empresas
  - Subtotal, IVA y Total
  - Estado del comprobante

- Botones de descarga:
  - **📥 Descargar XML**: Descarga el archivo XML del CFDI (formato SAT)
  - **📄 Descargar PDF**: Descarga el archivo PDF con formato profesional
  - **📋 Ver Detalles**: Muestra detalles adicionales del CFDI

## 📊 Estadísticas

En la parte superior de la sección de CFDIs verás un resumen:

- **CFDIs Emitidos**: Cantidad total de facturas que emitiste
- **CFDIs Recibidos**: Cantidad total de facturas que recibiste
- **Monto Emitido**: Suma total de facturas emitidas
- **Monto Recibido**: Suma total de facturas recibidas

## 🔄 Sincronización con SAT

El botón **"🔄 Sincronizar con SAT"** actualiza tu base de datos local con los últimos CFDIs disponibles en el portal del SAT.

**Proceso**:
1. Se conecta automáticamente al portal del SAT usando tus credenciales
2. Descarga los CFDIs de los últimos 12 meses
3. Almacena la información en caché local
4. Mostrará un mensaje con la cantidad de CFDIs importados

**Tiempo estimado**: 1-3 minutos (depende del portal SAT)

## 🔍 Filtros y Búsqueda

### Filtro por Tipo
- **emitido**: Muestra solo las facturas que TÚ emitiste
- **recibido**: Muestra solo las facturas que TÚ recibiste
- **todos**: Muestra ambos tipos

### Filtro por Estado
- **vigente**: CFDIs que están activos y válidos
- **cancelado**: CFDIs que han sido cancelados
- **todos**: Ambos tipos

### Rango de Fechas
El sistema automáticamente busca en los últimos 6 meses. Puedes modificar los parámetros en la URL:

```
?start_date=2025-01-01&end_date=2025-12-31
```

## 💾 Archivos Descargables

### Archivo XML
- **Formato**: XML válido según estándar SAT CFDI 4.0
- **Uso**: Importar a otros sistemas, procesar electrónicamente
- **Contenido**: 
  - Datos del emisor y receptor
  - Conceptos/productos/servicios
  - Impuestos (IVA, retenciones)
  - Total del comprobante

### Archivo PDF
- **Formato**: PDF profesional (estándar A4)
- **Uso**: Imprimir, enviar por email, archivar
- **Contenido**:
  - Detalles del CFDI con formato visual
  - Tabla de conceptos y montos
  - Información fiscal completa

## ⚙️ Configuración Avanzada

### Actualizar Contraseña SAT

Si cambiaste tu contraseña en el SAT:

1. Ve a **"🔐 Credenciales SAT"**
2. Haz clic en **"🔄 Actualizar Contraseña"**
3. Ingresa la nueva contraseña
4. Haz clic en **"✅ Confirmar Actualización"**

### Eliminar Credenciales

Para eliminar tus credenciales guardadas (por ejemplo, si compartirás la máquina):

1. Ve a **"🔐 Credenciales SAT"**
2. Haz clic en **"🗑️ Eliminar Credenciales"**
3. Confirma la acción

⚠️ **Esto eliminará las credenciales guardadas y no podrás descargar CFDIs hasta que las reconfigures**

### Subir Certificados de e.firma

Para autofirmar documentos (función futura):

1. Ve a **"🔐 Credenciales SAT"**
2. En la sección "📜 Certificado e.firma", haz clic en **"Subir archivo"**
3. Selecciona tu archivo `.cer` (certificado)
4. Selecciona tu archivo `.key` (llave privada)
5. Ingresa tu contraseña de la llave
6. Haz clic en **"📤 Subir Certificados"**

## 🐛 Solución de Problemas

### Problema: "No hay CFDIs para mostrar"

**Causas posibles**:
- No tienes CFDIs en el período seleccionado
- La búsqueda está muy filtrada

**Soluciones**:
- Amplía el rango de fechas
- Cambia los filtros a "todos"
- Haz clic en "Sincronizar con SAT" para descargar desde el portal

### Problema: "Error: Credenciales inválidas"

**Causas posibles**:
- RFC o contraseña incorrectos
- Cambió tu contraseña en el SAT

**Soluciones**:
- Verifica tu RFC (debe ser sin homoclave, 13 caracteres)
- Prueba tu contraseña accediendo directamente a: https://www.sat.gob.mx
- Actualiza las credenciales en la aplicación

### Problema: "Tiempo de espera agotado"

**Causas posibles**:
- Portal del SAT está lento
- Problemas de conexión a internet
- El SAT está en mantenimiento

**Soluciones**:
- Espera unos minutos e intenta de nuevo
- Verifica tu conexión a internet
- Consulta el estado del SAT en https://www.sat.gob.mx

### Problema: Los CFDIs no se actualizan

**Causas posibles**:
- Los datos están en caché local
- Necesitas sincronizar manualmente

**Soluciones**:
- Haz clic en "🔄 Sincronizar con SAT"
- Agrega `?use_cache=false` a la URL para forzar nueva descarga
- Recarga la página del navegador

## 📱 Descarga en Diferentes Formatos

### Exportar como Excel
[Próximamente] - Exporte todos los CFDIs a una hoja de cálculo Excel

### Exportar como CSV
[Próximamente] - Exporte los datos para analizar en Google Sheets o Excel

### Reportes PDF
[Próximamente] - Genere reportes personalizados de sus facturas

## 🔒 Privacidad y Seguridad

- ✅ Las credenciales se cifran con AES-256 antes de almacenarse
- ✅ Solo se desencriptan en memoria cuando se necesitan
- ✅ Los CFDIs solo son visibles para el usuario propietario
- ✅ Se valida la autenticación en cada operación
- ✅ No se registran credenciales en logs
- ✅ Las sesiones del navegador SAT se cierran inmediatamente después de uso

## ❓ Preguntas Frecuentes

### ¿Es seguro guardar mis credenciales SAT?
Sí, se almacenan cifradas con AES-256. Solo tú tienes acceso a ellas.

### ¿Cuántos CFDIs puedo descargar?
No hay límite técnico. El portal del SAT puede tener limitaciones.

### ¿Con qué frecuencia debo sincronizar?
Recomendamos sincronizar:
- Diariamente para usuarios activos
- Semanalmente para revisiones mensuales
- Mensualmente para auditorías

### ¿Puedo descargar CFDIs de años anteriores?
Sí, el SAT tiene disponibles CFDIs de los últimos años (varía según tu régimen).

### ¿Los archivos PDF son editables?
No, son PDFs de solo lectura para mantener la integridad de los datos.

### ¿Puedo descargar múltiples CFDIs a la vez?
Próximamente habilitaremos descarga múltiple en ZIP.

## 📞 Soporte

Si encuentras problemas:

1. Verifica la sección "🐛 Solución de Problemas"
2. Consulta el estado del SAT: https://www.sat.gob.mx
3. Revisa tu conexión a internet
4. Intenta nuevamente con otra sesión navegador

## 🎓 Términos Clave

- **CFDI**: Comprobante Fiscal Digital por Internet
- **RFC**: Registro Federal del Contribuyente
- **IVA**: Impuesto al Valor Agregado
- **Emisor**: Quien emite la factura (vende)
- **Receptor**: Quien recibe la factura (compra)
- **Vigente**: CFDI válido y activo
- **Cancelado**: CFDI que ha sido revocado/anulado
- **Descarga Masiva**: Función del SAT para descargar múltiples CFDIs

---

**Última actualización**: Diciembre 3, 2025
