# MIA — Assistant IA Local, RAG Hybride & Atelier Code

**MIA** est une interface de bureau Linux (PyQt6 / QWebEngine / QScintilla) 100 % locale et hors-ligne connectée à **Ollama**. Elle réunit un assistant conversationnel, un moteur de recherche documentaire hybride (ChromaDB + BM25), un mini-IDE avec comparateur Diff et des outils pédagogiques.

## Fonctionnalités principales

- **Chat IA & Profils spécialisés** : bascule instantanée entre modèles de code (`qwen2.5-coder`), raisonnement (`deepseek-r1`), cybersécurité offensive/défensive (`WhiteRabbitNeo`, `VulnLLM-R`, `Foundation-Sec`, `CyberSecQwen`) et vision (`minicpm-v`).
- **Conseil Cyber (Red vs Blue)** : audit séquentiel en 3 passes (attaque Red Team, correctif Blue Team et synthèse Purple Team).
- **RAG Hybride (ChromaDB + BM25)** : indexation locale de dossiers (PDF, Markdown, Python, Bash, logs) combinant recherche sémantique et recherche lexicale exacte avec citations cliquables.
- **Atelier Code QScintilla** : explorateur de projet, coloration syntaxique, vérification/exécution de scripts, auto-correction des erreurs par l'IA, comparateur visuel Diff et commandes Git intégrées.
- **Ingénierie Pédagogique & Rendu Scientifique** : éditeur d'équations LaTeX/KaTeX en direct, graphiques Chart.js, schémas Mermaid, export en diaporama HTML autonome, export QCM Moodle (`.gift`) et correcteur de copies par lot.
- **Moniteur Système** : suivi en temps réel de la RAM, de la VRAM NVIDIA, de la vitesse en tokens/s et bouton de purge VRAM.

## Prérequis (Ubuntu / Debian)

1. **Ollama** installé et démarré :
   ```bash
   curl -fsSL [https://ollama.com/install.sh](https://ollama.com/install.sh) | sh
   ollama pull qwen2.5-coder:7b
   ollama pull nomic-embed-text
   ```
2. **Paquets système** :
   ```bash
   sudo apt update && sudo apt install -y python3 python3-venv wget unzip
   ```

## Installation rapide

```bash
git clone [https://github.com/Ronan-Bozoc-cyber/mia-assistant.git](https://github.com/Ronan-Bozoc-cyber/mia-assistant.git)
cd mia-assistant
chmod +x install.sh
./install.sh
```

L'application est ensuite accessible directement depuis le menu d'applications sous le nom **MIA Assistant & IDE**.
