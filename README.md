# 🏛️ Gestor Fiscal Personal SAT

Sistema completo para gestionar trámites fiscales con el SAT (México). Automatiza descargas de CFDIs, gestiona e.firma, RFC, CURP y mantiene organizados todos tus documentos fiscales.

**La cartera fiscal digital del ciudadano mexicano** 🇲🇽

## ✨ Características

- 🔐 **Autenticación segura** con JWT y bcrypt
- 👤 **Gestión de perfil fiscal** (RFC, CURP, régimen fiscal)
- 📄 **Almacenamiento de documentos** (e.firma, constancias, CFDIs)
- 🔒 **Encriptación de credenciales SAT** con AES-256
- 🤖 **Automatización con Playwright** (descarga CFDIs, constancias)
- 🔔 **Notificaciones** de vencimientos y obligaciones fiscales
- 📊 **Dashboard intuitivo** con Streamlit

## 🚀 Inicio Rápido

### Opción 1: Script Automático (Recomendado)

```bash
git clone https://github.com/ALi3naTEd0/sat.git
cd sat
chmod +x setup.sh
./setup.sh
```

El script instalará todo automáticamente. Luego solo ejecuta:

```bash
./start.sh
```

Abre: **http://localhost:8501**

### Opción 2: Instalación Manual

#### Requisitos

- Python 3.13+
- PostgreSQL
- Redis
- Git

#### Pasos

```bash
# 1. Instalar dependencias del sistema
sudo pacman -S postgresql redis python libxml2 libxslt  # Arch
# o
sudo apt install postgresql redis libxml2-dev libxslt1-dev  # Ubuntu/Debian

# 2. Iniciar servicios
sudo systemctl start postgresql redis
sudo systemctl enable postgresql redis

# 3. Crear base de datos
sudo -u postgres createuser -s $USER
createdb sat_db

# 4. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar DATABASE_URL, generar claves

# 5. Crear entorno virtual e instalar dependencias
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 6. Crear tablas
cd backend
python create_tables.py
cd ..

# 7. Instalar navegadores (opcional)
playwright install chromium

# 8. ¡Iniciar!
./start.sh
```

## 📋 Casos de Uso

### 🟢 Caso A: Usuario con e.firma y contraseña SAT
- Autenticación automática
- Descarga de documentos fiscales
- Panel completo en tiempo real

### 🟡 Caso B: Usuario solo con RFC
- Validación de RFC
- Guía para activar contraseña SAT
- Guía para tramitar e.firma

### 🟠 Caso C: Usuario sin contraseña SAT
- Flujo de recuperación/creación de contraseña
- OCR de INE para autocompletar
- Asistente paso a paso

### 🔴 Caso D: Usuario sin RFC
- Consulta por CURP
- Generación de RFC guiada
- Prellenado inteligente de formularios

## 🔐 Seguridad

- Cifrado E2E de documentos sensibles
- Almacenamiento seguro de credenciales
- Tokens JWT con refresh
- Auditoría de accesos
- Cumplimiento GDPR/LFPDPPP

## 📱 Funcionalidades Core

1. **Identidad Fiscal**: RFC, CURP, Régimen, Obligaciones
2. **Documentos**: Almacenamiento cifrado de e.firma, constancias, INE
3. **CFDI**: Descarga automática de facturas emitidas/recibidas
4. **Declaraciones**: Historial y recordatorios
5. **Alertas**: Notificaciones de obligaciones y vencimientos
6. **Situación Fiscal**: Opinión del cumplimiento en tiempo real

## 🎯 MVP Roadmap

**Mes 1**: Backend + Autenticación + Gestión de usuarios
**Mes 2**: Automatización SAT + Gestión de documentos
**Mes 3**: App móvil + Panel fiscal + Alertas

---

## 🛠️ Instalación

Ver documentación específica en cada módulo:
- [Backend Setup](./backend/README.md)
- [Automation Setup](./automation/README.md)

## 📄 Licencia

Privado - Todos los derechos reservados
