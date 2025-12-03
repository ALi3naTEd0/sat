#!/bin/bash
# 🔍 Script de verificación rápida de la integración SAT

echo "🔍 Verificando integración SAT..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counter
PASSED=0
FAILED=0

# Check 1: Python modules
echo -n "1️⃣  Verificando módulos Python..."
if cd /Users/wilberthsanchez/sat/backend && \
   source ../.venv/bin/activate && \
   python -c "from app.automation.sat_automation import SATAutomation; from app.api.v1.endpoints.cfdi import router" 2>/dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Check 2: Config values
echo -n "2️⃣  Verificando configuración..."
if grep -q "HEADLESS_BROWSER" /Users/wilberthsanchez/sat/backend/app/core/config.py && \
   grep -q "SELENIUM_TIMEOUT" /Users/wilberthsanchez/sat/backend/app/core/config.py; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Check 3: reportlab installed
echo -n "3️⃣  Verificando dependencias (reportlab)..."
if cd /Users/wilberthsanchez/sat && \
   source .venv/bin/activate && \
   python -c "import reportlab" 2>/dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Check 4: Frontend function
echo -n "4️⃣  Verificando función show_cfdis()..."
if grep -q "def show_cfdis():" /Users/wilberthsanchez/sat/frontend/streamlit_app.py; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Check 5: API endpoints
echo -n "5️⃣  Verificando endpoints API..."
if grep -q "def list_cfdis" /Users/wilberthsanchez/sat/backend/app/api/v1/endpoints/cfdi.py && \
   grep -q "def sync_cfdis_from_sat" /Users/wilberthsanchez/sat/backend/app/api/v1/endpoints/cfdi.py && \
   grep -q "def download_cfdi_xml" /Users/wilberthsanchez/sat/backend/app/api/v1/endpoints/cfdi.py && \
   grep -q "def download_cfdi_pdf" /Users/wilberthsanchez/sat/backend/app/api/v1/endpoints/cfdi.py; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Check 6: Documentation
echo -n "6️⃣  Verificando documentación..."
if [ -f "/Users/wilberthsanchez/sat/INTEGRACION_SAT.md" ] && \
   [ -f "/Users/wilberthsanchez/sat/GUIA_USO_CFDIS.md" ] && \
   [ -f "/Users/wilberthsanchez/sat/ARQUITECTURA_CFDIS.md" ] && \
   [ -f "/Users/wilberthsanchez/sat/RESUMEN_IMPLEMENTACION.md" ]; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Check 7: Syntax errors
echo -n "7️⃣  Verificando errores de sintaxis..."
if cd /Users/wilberthsanchez/sat/backend && \
   python -m py_compile app/automation/sat_automation.py 2>/dev/null && \
   python -m py_compile app/api/v1/endpoints/cfdi.py 2>/dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Check 8: Router registration
echo -n "8️⃣  Verificando registro de routers..."
if grep -q "cfdi.router" /Users/wilberthsanchez/sat/backend/app/api/v1/router.py; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "✅ Passed: ${GREEN}${PASSED}${NC}/8"
echo -e "❌ Failed: ${RED}${FAILED}${NC}/8"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ¡Integración SAT lista para usar!${NC}"
    echo ""
    echo "📚 Documentación disponible:"
    echo "   • INTEGRACION_SAT.md - Documentación técnica"
    echo "   • GUIA_USO_CFDIS.md - Manual de usuario"
    echo "   • ARQUITECTURA_CFDIS.md - Diagramas"
    echo "   • RESUMEN_IMPLEMENTACION.md - Resumen de cambios"
    echo ""
    echo "🚀 Para iniciar:"
    echo "   ./start.sh"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  Hay problemas a resolver${NC}"
    exit 1
fi
