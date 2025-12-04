#!/bin/bash
# Setup script for new installations

set -e

echo "🏛️  Configurando Gestor Fiscal SAT"
echo "=================================="
echo ""

# Check if running on supported OS
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  Este script está optimizado para Linux (Arch/Ubuntu)"
    echo "   Ajusta los comandos según tu sistema operativo"
fi

# Check for required commands
REQUIRED_CMDS=("python3" "git")
for cmd in "${REQUIRED_CMDS[@]}"; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ $cmd no encontrado. Por favor instálalo primero."
        exit 1
    fi
done

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ $(echo "$PYTHON_VERSION < 3.11" | bc) -eq 1 ]]; then
    echo "❌ Se requiere Python 3.11 o superior (tienes $PYTHON_VERSION)"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION encontrado"
echo ""

# Install system dependencies based on OS
echo "📦 Instalando dependencias del sistema..."
if command -v brew &> /dev/null; then
    echo "   Detectado: macOS (Homebrew)"
    
    # Check if PostgreSQL is already installed
    if brew list postgresql@15 &>/dev/null || brew list postgresql &>/dev/null; then
        echo "   PostgreSQL ya está instalado"
    else
        brew install postgresql@15
    fi
    
    # Install other dependencies
    brew install redis libxml2 libxslt 2>/dev/null || echo "   Paquetes ya instalados"
    
    # Try to start services, ignore errors if already running
    echo "   Iniciando servicios..."
    brew services start postgresql@15 2>/dev/null || brew services restart postgresql@15 2>/dev/null || echo "   PostgreSQL: usando instancia existente"
    brew services start redis 2>/dev/null || brew services restart redis 2>/dev/null || echo "   Redis: usando instancia existente"
elif command -v pacman &> /dev/null; then
    echo "   Detectado: Arch Linux"
    sudo pacman -S --needed postgresql redis libxml2 libxslt
elif command -v apt &> /dev/null; then
    echo "   Detectado: Ubuntu/Debian"
    sudo apt update
    sudo apt install -y postgresql redis libxml2-dev libxslt1-dev python3-dev
else
    echo "⚠️  Sistema de paquetes no reconocido. Instala manualmente:"
    echo "   - PostgreSQL"
    echo "   - Redis"
    echo "   - libxml2"
    echo "   - libxslt"
    read -p "Presiona Enter cuando hayas instalado las dependencias..."
fi

# Start and enable services
echo ""
echo "🚀 Iniciando servicios..."
if command -v brew &> /dev/null; then
    # macOS - services already started with brew services
    echo "✅ Servicios iniciados con Homebrew"
else
    # Linux - use systemctl
    sudo systemctl start postgresql redis || sudo systemctl start postgresql valkey
    sudo systemctl enable postgresql redis || sudo systemctl enable postgresql valkey
fi

# Setup PostgreSQL
echo ""
echo "🗄️  Configurando PostgreSQL..."
if command -v brew &> /dev/null; then
    # macOS - wait for PostgreSQL to be ready
    echo "   Esperando a que PostgreSQL esté listo..."
    sleep 3
    
    # Try to connect and create database
    for i in {1..10}; do
        if psql postgres -c "SELECT 1" &>/dev/null; then
            break
        fi
        echo "   Reintento $i/10..."
        sleep 2
    done
    
    if ! psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw sat_db; then
        createdb sat_db 2>/dev/null && echo "✅ Base de datos 'sat_db' creada" || echo "⚠️  No se pudo crear la base de datos automáticamente. Créala manualmente con: createdb sat_db"
    else
        echo "✅ Base de datos 'sat_db' ya existe"
    fi
else
    # Linux - needs postgres user
    if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw sat_db; then
        sudo -u postgres createuser -s $USER 2>/dev/null || echo "Usuario ya existe"
        createdb sat_db
        echo "✅ Base de datos 'sat_db' creada"
    else
        echo "✅ Base de datos 'sat_db' ya existe"
    fi
fi

# Create .env from example
echo ""
echo "⚙️  Configurando variables de entorno..."
if [ ! -f .env ]; then
    cp .env.example .env
    
    # Replace placeholder with actual username
    sed -i "s/your_user/$USER/g" .env
    
    # Generate JWT secret
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/your-secret-key-change-this-in-production/$JWT_SECRET/g" .env
    
    # Generate encryption key
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    sed -i "s/change-this-to-a-generated-fernet-key/$ENCRYPTION_KEY/g" .env
    
    echo "✅ Archivo .env creado con claves generadas"
else
    echo "ℹ️  .env ya existe, no se sobrescribirá"
fi

# Create virtual environment
echo ""
echo "🐍 Creando entorno virtual..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Entorno virtual creado"
else
    echo "ℹ️  Entorno virtual ya existe"
fi

# Activate venv and install dependencies
echo ""
echo "📦 Instalando dependencias de Python..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# Create database tables
echo ""
echo "🗄️  Creando tablas en la base de datos..."
cd backend
python create_tables.py
cd ..

# Install Playwright browsers
echo ""
read -p "¿Instalar navegadores para automatización? (s/n): " install_browsers
if [[ $install_browsers == "s" || $install_browsers == "S" ]]; then
    playwright install chromium
    echo "✅ Navegadores instalados"
fi

# Make scripts executable
echo ""
echo "🔧 Configurando permisos..."
chmod +x start.sh
chmod +x scripts/*.sh 2>/dev/null || true

echo ""
echo "=================================="
echo "✅ ¡Instalación completada!"
echo "=================================="
echo ""
echo "Para iniciar la aplicación:"
echo "   ./start.sh"
echo ""
echo "Luego abre: http://localhost:8501"
echo ""
echo "Documentación:"
echo "   - README.md - Guía general"
echo "   - COMO_FUNCIONA.md - Arquitectura técnica"
echo "   - README_QUICK_START.md - Inicio rápido"
echo ""
