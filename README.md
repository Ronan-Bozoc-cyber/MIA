# MIA — Assistant IA Local, RAG Hybride & Atelier Code

**MIA** est une interface de bureau Linux (PyQt6 / QWebEngine / QScintilla) 100 % locale et hors-ligne connectée à **Ollama**. Elle réunit un assistant conversationnel calibré pour les PC portables (4 Go VRAM ou CPU), un moteur de recherche documentaire hybride (ChromaDB + BM25), un mini-IDE avec comparateur Diff, des outils pédagogiques et des outils de gestion des biais (**Heretic / GGUF**).

## Fonctionnalités principales

- **Chat IA & 18 Profils spécialisés** : bascule instantanée entre modèles rapides 4 Go VRAM (`qwen2.5-coder:3b`, `qwen2.5:3b-instruct`, `CyberSecQwen-4B`, `qwen3:4b`, `llama3.2:3b`), modèles 7B/8B (`qwen2.5-coder:7b`, `deepseek-r1`, `WhiteRabbitNeo`, `VulnLLM-R`, `Foundation-Sec`, `RedSage`) et vision (`minicpm-v`).
- **Optimisation Matérielle Automatique (RTX 2050 4 Go / PC modestes)** : détection CPU/RAM/VRAM au démarrage, paliers `⚡ Éco 4Go` / `⚖️ Standard` / `🚀 Max`, contrôle `num_ctx` rapide (`4k`/`8k`/`12k`/`16k`), réglage `num_thread` (cœurs physiques), `num_batch`, `num_gpu`, quantification HF 4 Go (`IQ4_XS` / `Q3_K_M`), purge VRAM globale via `/api/ps` et script `optimize_ollama.sh` (Flash Attention + KV-cache `q8_0`/`q4_0`).
- **Gestion des Biais & Studio Heretic** : importateur `.gguf` → `Modelfile` → Ollama en 1 clic, **Banc de Test des Biais** (Anti-Sycophancy, Anti-Slop, Anti-Faux-Refus) et **Studio Heretic** (mode local `bnb_4bit` pour modèles ≤ 4B + générateur de Notebook Colab T4 / script serveur GPU pour 7B–8B → GGUF).
- **Conseil Cyber (Red vs Blue vs Purple)** : audit séquentiel en 3 passes avec purge VRAM automatique entre les passes et préréglage rapide 4 Go.
- **RAG Hybride (ChromaDB + BM25)** : indexation locale de dossiers (PDF, Markdown, Python, Bash, logs) avec cache mémoire BM25/Chroma, citations cliquables et déchargement automatique de l'embedding pour préserver la VRAM.
- **Atelier Code QScintilla** : explorateur de projet, coloration syntaxique (6 langages), vérification/exécution de scripts, auto-correction des erreurs par l'IA, comparateur visuel Diff et commandes Git intégrées.
- **Ingénierie Pédagogique & Rendu Scientifique** : éditeur d'équations LaTeX/KaTeX en direct, graphiques Chart.js, schémas Mermaid, export en diaporama HTML autonome, export QCM Moodle (`.gift`), DokuWiki et correcteur de copies par lot annulable.
- **Gestionnaire de Modèles & Moniteur Système** : suivi en temps réel de la RAM, VRAM NVIDIA, vitesse en tokens/s, taille disque des modèles Ollama et suppression en 1 clic.

## Prérequis (Ubuntu / Debian)

1. **Ollama** installé et démarré :
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull qwen2.5-coder:3b
   ollama pull nomic-embed-text
   ```
2. **Paquets système** :
   ```bash
   sudo apt update && sudo apt install -y python3 python3-venv wget unzip
   ```

## Installation rapide

```bash
git clone https://github.com/Ronan-Bozoc-cyber/MIA.git
cd MIA
chmod +x install.sh optimize_ollama.sh
./install.sh
```

Pour activer **Flash Attention + KV-Cache quantifié** sur Ollama (fortement recommandé pour les GPU 4 Go VRAM comme la RTX 2050) :

```bash
sudo ./optimize_ollama.sh q8_0
```

L'application est ensuite accessible directement depuis le menu d'applications sous le nom **MIA Assistant & IDE** (interface isolée sur l'iGPU afin de dédier 100 % de la VRAM NVIDIA à Ollama).
