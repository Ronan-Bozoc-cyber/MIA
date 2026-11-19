#!/bin/bash
set -e

echo "⚡ Optimisation du service Ollama pour GPU 4 Go VRAM (ex. RTX 2050 Ampere)..."

KV_TYPE="${1:-q8_0}"
if [[ "$KV_TYPE" != "q8_0" && "$KV_TYPE" != "q4_0" ]]; then
    echo "Usage : sudo ./optimize_ollama.sh [q8_0|q4_0]"
    exit 1
fi

DROPIN_DIR="/etc/systemd/system/ollama.service.d"
DROPIN_FILE="$DROPIN_DIR/mia-opt.conf"

sudo mkdir -p "$DROPIN_DIR"
sudo tee "$DROPIN_FILE" > /dev/null << EOF
[Service]
# Optimisations MIA pour PC portable / GPU 4 Go VRAM (RTX 2050 Ampere)
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=$KV_TYPE"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_NUM_PARALLEL=1"
EOF

echo "🔄 Rechargement de systemd et redémarrage d'Ollama..."
sudo systemctl daemon-reload
sudo systemctl restart ollama

echo ""
echo "✅ Optimisations appliquées dans $DROPIN_FILE :"
echo "   - OLLAMA_FLASH_ATTENTION=1 (accélération Ampere + économie VRAM)"
echo "   - OLLAMA_KV_CACHE_TYPE=$KV_TYPE (KV-cache quantifié)"
echo "   - OLLAMA_MAX_LOADED_MODELS=1 (évite la saturation 4 Go VRAM / 16 Go RAM)"
echo "   - OLLAMA_NUM_PARALLEL=1 (mono-utilisateur optimisé)"
echo "👉 Astuce : pour un contexte encore plus compact, relance avec : sudo ./optimize_ollama.sh q4_0"
