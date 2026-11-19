#!/bin/bash
set -e

echo "🚀 Installation de MIA - Assistant IA Souverain & Atelier Code..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/mia-app"
DESKTOP_FILE="$HOME/.local/share/applications/mia-assistant.desktop"

for cmd in python3 wget unzip; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "❌ L'outil '$cmd' est manquant. Installe-le avec : sudo apt install -y python3 python3-venv wget unzip"
        exit 1
    fi
done

mkdir -p "$APP_DIR/conversations" "$APP_DIR/chroma_dbs" "$APP_DIR/mermaid" "$APP_DIR/chartjs"
mkdir -p "$HOME/.local/share/applications"

cp "$SCRIPT_DIR/app.py" "$APP_DIR/app.py"
cp "$SCRIPT_DIR/requirements.txt" "$APP_DIR/requirements.txt"

if [ ! -d "$APP_DIR/venv" ]; then
    echo "🐍 Création de l'environnement virtuel Python..."
    python3 -m venv "$APP_DIR/venv"
fi

echo "📦 Installation des dépendances Python..."
"$APP_DIR/venv/bin/pip" install --upgrade pip -q
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q

if [ ! -d "$APP_DIR/katex" ]; then
    echo "🧮 Téléchargement de KaTeX (rendu mathématique hors-ligne)..."
    wget -q 'https://github.com/KaTeX/KaTeX/releases/download/v0.16.8/katex.zip' -O "$APP_DIR/katex.zip"
    unzip -q "$APP_DIR/katex.zip" -d "$APP_DIR"
    rm -f "$APP_DIR/katex.zip"
fi

if [ ! -f "$APP_DIR/mermaid/mermaid.min.js" ]; then
    echo "🗺️ Téléchargement de Mermaid..."
    wget -q 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js' -O "$APP_DIR/mermaid/mermaid.min.js"
fi

if [ ! -f "$APP_DIR/chartjs/chart.min.js" ]; then
    echo "📊 Téléchargement de Chart.js..."
    wget -q 'https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js' -O "$APP_DIR/chartjs/chart.min.js"
fi

cat << DESKTOP > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=MIA Assistant & IDE
Comment=Assistant IA Local, RAG Hybride, Pédagogie et Atelier Code QScintilla
Exec=$APP_DIR/venv/bin/python $APP_DIR/app.py
Icon=utilities-terminal
Terminal=false
Categories=Development;Education;Office;
DESKTOP

chmod +x "$DESKTOP_FILE"

if [ -d "$HOME/Bureau" ]; then
    cp "$DESKTOP_FILE" "$HOME/Bureau/"
    chmod +x "$HOME/Bureau/mia-assistant.desktop"
elif [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_FILE" "$HOME/Desktop/"
    chmod +x "$HOME/Desktop/mia-assistant.desktop"
fi

echo ""
echo "✅ Installation de MIA terminée !"
if ! command -v ollama >/dev/null 2>&1; then
    echo "⚠️  Ollama n'est pas détecté sur cette machine."
    echo "👉 Installe-le avec : curl -fsSL https://ollama.com/install.sh | sh"
    echo "👉 Puis télécharge un modèle : ollama pull qwen2.5-coder:7b && ollama pull nomic-embed-text"
else
    echo "👉 Lance MIA depuis ton menu d'applications ou via : $APP_DIR/venv/bin/python $APP_DIR/app.py"
fi
