# 🏛️ Gestor Fiscal Personal SAT

Sistema completo para gestionar trámites fiscales con el SAT (México). Automatiza descargas de CFDIs usando la **API oficial del SAT** (Web Services SOAP), gestiona e.firma, RFC, CURP y mantiene organizados todos tus documentos fiscales.

**La cartera fiscal digital del ciudadano mexicano** 🇲🇽

## ✨ Características

- 🔐 **Autenticación segura** con JWT y bcrypt
- 👤 **Gestión de perfil fiscal** (RFC, CURP, régimen fiscal)
- 📄 **Almacenamiento de documentos** (e.firma, constancias, CFDIs)
- 🔒 **Encriptación de credenciales** con AES-256
- 🌐 **Web Services oficiales del SAT** - Descarga masiva de CFDIs con e.firma
- 📦 **Procesamiento automático** de paquetes ZIP y parseo de XMLs (CFDI 3.3 y 4.0)
- 🔔 **Notificaciones** de vencimientos y obligaciones fiscales
- 📊 **Dashboard intuitivo** con Streamlit

## 🚀 Inicio Rápido

### Opción 1: Script Automático (Recomendado)

```bash
git clone https://github.com/ALi3naTEd0/sat.git
cd sat
chmod +x scripts/setup.sh
./scripts/setup.sh
```

El script instalará todo automáticamente. Luego solo ejecuta:

```bash
./scripts/start.sh
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

## macOS
brew install postgresql@15 redis libxml2 libxslt python@3.13
brew services start postgresql@15
brew services start redis

## Arch Linux
sudo pacman -S postgresql redis python libxml2 libxslt

## Ubuntu/Debian
sudo apt install postgresql redis libxml2-dev libxslt1-dev

# 2. Iniciar servicios (solo Linux)
sudo systemctl start postgresql redis
sudo systemctl enable postgresql redis

# 3. Crear base de datos

## macOS
createuser -s $USER  # No requiere sudo
createdb sat_db

## Linux
sudo -u postgres createuser -s $USER
createdb sat_db

# 4. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar DATABASE_URL, generar claves

# 5. Crear entorno virtual e instalar dependencias
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 6. ¡Iniciar! (las tablas se crean automáticamente)
./scripts/start.sh
```

**Nota:** Las tablas de la base de datos se crean automáticamente al iniciar el backend. No necesitas ejecutar scripts adicionales.

## 🔑 Requisitos para Sincronización SAT

Para descargar CFDIs del SAT necesitas:
- ✅ **RFC** configurado en tu perfil fiscal
- ✅ **e.firma** (.cer + .key + contraseña)

### ¿Cómo obtener tu e.firma?
Si no tienes e.firma, puedes tramitarla en: https://www.sat.gob.mx/tramites/16703/obten-tu-certificado-de-e-firma-portabilidad

## 🔐 Seguridad

- Cifrado E2E de documentos sensibles
- Almacenamiento seguro de credenciales
- Tokens JWT con refresh
- Auditoría de accesos
- Cumplimiento GDPR/LFPDPPP

## 📱 Funcionalidades

### ✅ Implementadas
- 🔐 Autenticación y gestión de usuarios
- 👤 Perfiles fiscales (RFC, CURP, régimen)
- 📄 Gestión de documentos y e.firma
- 🌐 Sincronización con Web Services SAT (descarga masiva)
- 📦 Procesamiento automático de CFDIs
- 📊 Dashboard fiscal con estadísticas
- 🧾 Visualización y gestión de facturas

### 🚧 En Desarrollo
- 📋 Declaraciones y prellenado automático
- 🔔 Sistema de alertas y recordatorios
- 📈 Análisis fiscal avanzado

## 🏗️ Arquitectura

```
├── backend/          # FastAPI + PostgreSQL
│   ├── app/
│   │   ├── api/      # Endpoints REST
│   │   ├── models/   # Modelos SQLAlchemy
│   │   ├── services/ # Lógica de negocio
│   │   └── core/     # Config y seguridad
│   └── alembic/      # Migraciones DB
├── frontend/         # Streamlit UI
├── scripts/          # Scripts de utilidad
└── docs/             # Documentación (GitHub Pages)
```

## 🔧 Stack Tecnológico

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Frontend**: Streamlit
- **Seguridad**: JWT, bcrypt, AES-256
- **Web Services**: Zeep (SOAP client), cryptography (e.firma)
- **Procesamiento**: lxml (XML parsing)

## 📄 Licencia

Privado - Todos los derechos reservados
