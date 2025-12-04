#!/bin/bash

# Gestor Fiscal SAT - Run Script
# Este script inicia todos los servicios necesarios

set -e

echo "🏛️  Gestor Fiscal Personal SAT"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Archivo .env no encontrado${NC}"
    echo "Copiando .env.example a .env..."
    cp .env.example .env
    echo -e "${BLUE}⚠️  Por favor configura las variables en .env antes de continuar${NC}"
    exit 1
fi

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment no encontrado${NC}"
    echo "Creando virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activando entorno virtual...${NC}"
source .venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${BLUE}📦 Instalando dependencias del backend...${NC}"
    pip install -r backend/requirements.txt
fi

if ! python -c "import streamlit" 2>/dev/null; then
    echo -e "${BLUE}📦 Instalando dependencias del frontend...${NC}"
    pip install -r frontend/requirements.txt
fi

# Check Docker services
echo -e "${BLUE}🐳 Verificando servicios Docker...${NC}"
if ! docker ps | grep -q "sat.*postgres"; then
    echo "Iniciando PostgreSQL y Redis..."
    docker-compose up -d postgres redis
    echo "Esperando a que la base de datos esté lista..."
    sleep 5
fi

# Check if database is initialized
echo -e "${BLUE}🗄️  Verificando base de datos...${NC}"
cd backend
if [ ! -d "alembic/versions" ] || [ -z "$(ls -A alembic/versions)" ]; then
    echo "Creando migración inicial..."
    alembic revision --autogenerate -m "Initial migration"
fi

echo "Aplicando migraciones..."
alembic upgrade head
cd ..

# Function to cleanup on exit
cleanup() {
    echo -e "\n${BLUE}🛑 Deteniendo servicios...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}🚀 Iniciando Backend API (http://localhost:8000)${NC}"
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "Esperando a que el backend esté listo..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend listo${NC}"
        break
    fi
    sleep 1
done

# Start frontend
echo -e "${GREEN}🎨 Iniciando Frontend Streamlit (http://localhost:8501)${NC}"
cd frontend
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}✅ Todos los servicios están corriendo${NC}"
echo ""
echo "📝 URLs:"
echo "   Frontend:  http://localhost:8501"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/api/v1/docs"
echo ""
echo "📋 Logs:"
echo "   Backend:   tail -f backend.log"
echo "   Frontend:  tail -f frontend.log"
echo ""
echo -e "${BLUE}Presiona Ctrl+C para detener todos los servicios${NC}"

# Wait for processes
wait
