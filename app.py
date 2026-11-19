import sys, json, os, base64, shutil, urllib.parse, re, subprocess, difflib
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.wayland*=false'
from datetime import datetime
import requests
import psutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QPushButton, QTextEdit,
                             QComboBox, QSplitter, QFileDialog, QMessageBox, QLabel,
                             QDialog, QDialogButtonBox, QCheckBox, QLineEdit,
                             QFormLayout, QDoubleSpinBox, QSpinBox, QTreeView, QTabWidget,
                             QSystemTrayIcon, QMenu, QStyle, QInputDialog, QProgressDialog,
                             QStatusBar, QSizePolicy)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtCore import QThread, pyqtSignal, QUrl, Qt, QDir, QTimer
from PyQt6.QtGui import (QAction, QStandardItemModel, QStandardItem, QFont,
                         QColor, QFileSystemModel, QKeySequence, QShortcut, QDesktopServices)
from PyQt6.Qsci import (QsciScintilla, QsciLexerPython, QsciLexerBash,
                        QsciLexerJSON, QsciLexerYAML, QsciLexerMarkdown, QsciLexerSQL)
import markdown

APP_DIR = os.path.expanduser("~/.local/share/mia-app")
CONV_DIR = os.path.join(APP_DIR, "conversations")
PROFILES_FILE = os.path.join(APP_DIR, "profiles.json")
LIBRARIES_FILE = os.path.join(APP_DIR, "libraries.json")
os.makedirs(CONV_DIR, exist_ok=True)
os.makedirs(os.path.join(APP_DIR, "chroma_dbs"), exist_ok=True)

GRAPH_INSTRUCTIONS = (
    "\n\nRÈGLES POUR LES GRAPHIQUES ET SCHÉMAS :\n"
    "1. Pour tracer une courbe, un histogramme ou un camembert, utilise OBLIGATOIREMENT un bloc ```plot avec ce format exact de 4 lignes :\n"
    "```plot\n"
    "type: line\n"
    "label: Courbe de Gauss\n"
    "x: [-4, -3, -2, -1, 0, 1, 2, 3, 4]\n"
    "y: [0.0003, 0.0044, 0.054, 0.242, 0.398, 0.242, 0.054, 0.0044, 0.0003]\n"
    "```\n"
    "(Remplace 'line' par 'bar' pour un histogramme ou 'pie' par un camembert).\n"
    "2. Pour un organigramme ou schéma réseau, utilise ```mermaid avec les textes entre guillemets : graph TD; A[\"Serveur\"] --> B[\"Client\"];"
)

DEFAULT_PROFILES = {
    "DevSecOps & Code (Qwen Coder 7B)": {
        "model": "qwen2.5-coder:7b",
        "temperature": 0.15,
        "num_ctx": 12288,
        "sys": "Tu es architecte logiciel et expert Linux/Python/Docker. Écris du code complet, robuste, sécurisé et directement exécutable." + GRAPH_INSTRUCTIONS
    },
    "VulnLLM-R 7B (Audit de Code & Failles SAST)": {
        "model": "hf.co/MaziyarPanahi/VulnLLM-R-7B-GGUF:Q4_K_M",
        "temperature": 0.1,
        "num_ctx": 12288,
        "sys": "Tu es VulnLLM-R, expert en détection de vulnérabilités logicielles (CWE, OWASP, SAST). Analyse le flux de données ligne par ligne, identifie les failles exactes, explique le vecteur d'exploitation et fournis le correctif sécurisé." + GRAPH_INSTRUCTIONS
    },
    "Cisco Foundation-Sec 8B (SOC, SIEM & Threat Intel)": {
        "model": "hf.co/gabriellarson/Foundation-Sec-8B-Instruct-GGUF:Q4_K_M",
        "temperature": 0.25,
        "num_ctx": 8192,
        "sys": "Tu es Foundation-Sec (Cisco), expert Blue Team, SOC, DFIR et Threat Intelligence. Analyse les logs (Suricata, Wazuh, pfSense, Syslog), mappe les tactiques MITRE ATT&CK, évalue les CVE et propose des playbooks de remédiation." + GRAPH_INSTRUCTIONS
    },
    "RedSage 8B (Généraliste Cyber, NIST & EBIOS RM)": {
        "model": "hf.co/mradermacher/RedSage-8B-Cyber-GGUF:Q4_K_M",
        "temperature": 0.35,
        "num_ctx": 8192,
        "sys": "Tu es RedSage-8B, assistant généraliste de cybersécurité maîtrisant les normes (ISO 27001, NIST, EBIOS RM, RGPD), les RFC réseau et l'administration Linux. Explique chaque concept avec rigueur et pédagogie." + GRAPH_INSTRUCTIONS
    },
    "CyberSecQwen 4B (Défense Rapide & Hardening VRAM)": {
        "model": "hf.co/mradermacher/CyberSecQwen-4B-GGUF:Q4_K_M",
        "temperature": 0.2,
        "num_ctx": 8192,
        "sys": "Tu es CyberSecQwen-4B, modèle compact ultra-rapide spécialisé dans la défense système, le durcissement Linux/SSH, les règles de filtrage pare-feu (pfSense, nftables, iptables) et la sécurisation d'infrastructure." + GRAPH_INSTRUCTIONS
    },
    "WhiteRabbitNeo (Red Team & Pentest Offensif)": {
        "model": "jimscard/whiterabbit-neo",
        "temperature": 0.25,
        "num_ctx": 8192,
        "sys": "Tu es WhiteRabbitNeo, assistant Red Team et pentest offensif pour des audits autorisés et laboratoires Cyber-Range. Détaille les méthodologies de reconnaissance, d'énumération, d'exploitation et les contre-mesures associées." + GRAPH_INSTRUCTIONS
    },
    "BugTraceAI-CORE (Bug Bounty & AppSec Web)": {
        "model": "hf.co/BugTraceAI/BugTraceAI-CORE-Pro",
        "temperature": 0.2,
        "num_ctx": 8192,
        "sys": "Tu es BugTraceAI-CORE, expert en sécurité applicative Web (OWASP Top 10, API, SQLi, XSS, SSRF, IDOR) et Bug Bounty. Analyse les requêtes HTTP, identifie les failles logiques et rédige des rapports d'audit reproductibles." + GRAPH_INSTRUCTIONS
    },
    "BaronLLM v2 8B (Simulation Adversaire & Red Team)": {
        "model": "huihui_ai/baronllm-abliterated",
        "temperature": 0.25,
        "num_ctx": 8192,
        "sys": "Tu es BaronLLM, expert en recherche offensive, simulation d'adversaire, analyse d'attaques Active Directory/Linux et développement d'outils d'audit type M-SCAN." + GRAPH_INSTRUCTIONS
    },
    "Lily Cybersecurity 7B (Scénarios CTF & TP Cyber)": {
        "model": "hf.co/segolilylabs/Lily-Cybersecurity-7B-GGUF:Q4_K_M",
        "temperature": 0.3,
        "num_ctx": 8192,
        "sys": "Tu es Lily-Cybersecurity, spécialiste des environnements CTF, des laboratoires de cybersécurité et du piratage éthique pédagogique." + GRAPH_INSTRUCTIONS
    },
    "Cybersécurité & Raisonnement (DeepSeek R1 7B)": {
        "model": "deepseek-r1:7b",
        "temperature": 0.3,
        "num_ctx": 8192,
        "sys": "Tu es expert en cybersécurité, administration système et gouvernance des données. Analyse les vulnérabilités et logs avec rigueur." + GRAPH_INSTRUCTIONS
    },
    "Ingénierie Pédagogique (Qwen 7B)": {
        "model": "qwen2.5:7b-instruct",
        "temperature": 0.5,
        "num_ctx": 12288,
        "sys": "Tu es ingénieur pédagogique senior. Rédige des supports de cours structurés, des travaux pratiques pas-à-pas et des études de cas concrètes." + GRAPH_INSTRUCTIONS
    },
    "Rédaction & Édition Fluide (Mistral 7B)": {
        "model": "mistral:7b-instruct",
        "temperature": 0.6,
        "num_ctx": 8192,
        "sys": "Tu es un éditeur humain professionnel et senior. Améliore le rythme, la fluidité, les transitions et le ton. Élimine les formulations robotiques et rends l'écriture naturelle, captivante et facile à lire." + GRAPH_INSTRUCTIONS
    },
    "Analyse Visuelle & Schémas (Vision MiniCPM)": {
        "model": "minicpm-v:8b",
        "temperature": 0.2,
        "num_ctx": 8192,
        "sys": "Tu es expert en cybersécurité et architecture réseau. Analyse avec précision les images, captures d'écran d'erreurs et schémas techniques fournis."
    },
    "Mode Rapide / Batterie (Llama 3.2 3B)": {
        "model": "llama3.2:3b",
        "temperature": 0.4,
        "num_ctx": 8192,
        "sys": "Tu es un assistant technique concis et ultra-rapide. Va droit au but." + GRAPH_INSTRUCTIONS
    }
}

QUICK_PROMPTS = {
    "⚡ Actions rapides...": "",
    "🎓 Plan de cours + TP + QCM": "Conçois un module de formation complet sur le sujet suivant : [SUJET].\nSépare chaque grande section par '---' pour permettre l'export en diapositives.\nStructure attendue :\n1. Objectifs pédagogiques\n2. Cours théorique détaillé avec schémas/exemples\n3. Travaux Pratiques (TP) pas-à-pas sous Linux\n4. QCM d'évaluation de 5 questions avec corrigé détaillé.",
    "🎯 Générer QCM au format Moodle GIFT": "Génère un QCM de 5 questions sur le sujet : [SUJET].\nUtilise EXCLUSIVEMENT la syntaxe officielle Moodle GIFT dans un bloc ```gift :\n::Titre Question:: Énoncé de la question {\n=Bonne réponse #Bravo\n~Mauvaise réponse 1 #Explication\n~Mauvaise réponse 2 #Explication\n}",
    "🛡️ Audit de sécurité (Code / Config)": "Réalise un audit de sécurité approfondi du code ou fichier de configuration ci-dessous.\nIdentifie :\n1. Les vulnérabilités ou erreurs de configuration\n2. Le niveau de criticité\n3. Le correctif exact prêt à être appliqué.\n\n",
    "🔍 Analyse de logs (Suricata / Wazuh / Syslog)": "Analyse les traces/logs suivants. Identifie la source, la nature de l'anomalie ou de l'attaque, et propose la règle de filtrage ou de remédiation adaptée :\n\n",
    "📝 Réécriture fluide et naturelle": "Agis comme un éditeur humain senior. Réécris le texte suivant pour améliorer le rythme, la fluidité et les transitions, en éliminant toute tournure robotique :\n\n",
    "📚 Convertir en syntaxe DokuWiki": "Convertis le texte suivant en syntaxe DokuWiki stricte (4 espaces avant l'étoile '    *' pour les listes à puces, '----' pour les traits horizontaux, '[[url|texte]]' pour les liens, et pas de majuscule juste après deux-points) :\n\n"
}

if not os.path.exists(PROFILES_FILE):
    with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_PROFILES, f, indent=4, ensure_ascii=False)

if not os.path.exists(LIBRARIES_FILE):
    with open(LIBRARIES_FILE, 'w', encoding='utf-8') as f:
        json.dump({}, f, indent=4, ensure_ascii=False)

MODERN_QSS = """
QMainWindow, QDialog { background-color: #1e1e2e; }
QWidget { color: #cdd6f4; font-family: 'Ubuntu', sans-serif; font-size: 13px; }
QPushButton { background-color: #313244; border: 1px solid #45475a; border-radius: 6px; padding: 5px 10px; font-weight: bold; }
QPushButton:hover { background-color: #45475a; border: 1px solid #585b70; }
QPushButton:pressed { background-color: #181825; }
QTextEdit, QListWidget, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QTreeView { background-color: #11111b; color: #cdd6f4; border: 1px solid #313244; border-radius: 6px; padding: 5px; }
QTextEdit:focus, QListWidget:focus, QComboBox:focus, QLineEdit:focus, QTreeView:focus { border: 1px solid #89b4fa; }
QComboBox QAbstractItemView { background-color: #1e1e2e; color: #cdd6f4; selection-background-color: #89b4fa; selection-color: #11111b; border: 1px solid #313244; }
QListWidget::item, QTreeView::item { padding: 5px; border-radius: 4px; }
QListWidget::item:selected, QTreeView::item:selected { background-color: #89b4fa; color: #11111b; font-weight: bold; }
QListWidget::item:hover:!selected, QTreeView::item:hover:!selected { background-color: #313244; }
QSplitter::handle { background-color: #181825; width: 4px; height: 4px; }
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #585b70; background: #181825; }
QCheckBox::indicator:checked { background: #89b4fa; border: 1px solid #89b4fa; }
QTabWidget::pane { border: 1px solid #313244; border-radius: 6px; background: #11111b; }
QTabBar::tab { background: #181825; color: #a6adc8; padding: 6px 12px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
QTabBar::tab:selected { background: #313244; color: #89b4fa; font-weight: bold; }
QMenu { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; padding: 4px; }
QMenu::item { padding: 6px 20px; border-radius: 4px; }
QMenu::item:selected { background-color: #89b4fa; color: #11111b; font-weight: bold; }
QStatusBar { background-color: #181825; color: #a6adc8; border-top: 1px solid #313244; font-size: 12px; }
"""

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="katex/katex.min.css">
    <script defer src="katex/katex.min.js"></script>
    <script defer src="katex/contrib/auto-render.min.js"></script>
    <script src="mermaid/mermaid.min.js"></script>
    <script src="chartjs/chart.min.js"></script>
    <style>
        body { font-family: 'Ubuntu', sans-serif; background: #1e1e2e; color: #cdd6f4; margin: 0; padding: 16px; font-size: 14.5px; }
        .chat-container { display: flex; flex-direction: column; gap: 16px; padding-bottom: 20px; }
        .msg-row { display: flex; width: 100%; }
        .msg-row.user { justify-content: flex-end; }
        .msg-row.assistant { justify-content: flex-start; }
        .msg-bubble { position: relative; max-width: 90%; padding: 14px 18px; border-radius: 12px; line-height: 1.55; box-shadow: 0 3px 6px rgba(0,0,0,0.12); overflow-wrap: break-word; }
        .msg-bubble.user { background: #89b4fa; color: #11111b; border-bottom-right-radius: 2px; }
        .msg-bubble.assistant { background: #313244; color: #cdd6f4; border-bottom-left-radius: 2px; border: 1px solid #45475a; padding-top: 32px; }
        .copy-btn { position: absolute; top: 6px; right: 8px; background: transparent; border: none; color: #a6adc8; cursor: pointer; font-size: 15px; opacity: 0.6; transition: 0.2s; z-index: 10; }
        .copy-btn:hover { opacity: 1; transform: scale(1.1); }
        .rag-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
        .rag-badge { background: #181825; color: #a6e3a1; border: 1px solid #a6e3a1; border-radius: 12px; padding: 2px 10px; font-size: 11.5px; cursor: pointer; transition: 0.2s; }
        .rag-badge:hover { background: #a6e3a1; color: #11111b; font-weight: bold; }
        .code-wrapper { position: relative; margin: 10px 0; }
        .code-header { display: flex; justify-content: space-between; align-items: center; background: #181825; color: #a6adc8; padding: 4px 12px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-size: 11.5px; font-family: monospace; border: 1px solid #181825; border-bottom: none; }
        .code-actions { display: flex; gap: 6px; }
        .copy-code-btn { background: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 2px 8px; cursor: pointer; font-size: 11px; }
        .copy-code-btn:hover { background: #89b4fa; color: #11111b; }
        .send-ide-btn { background: #a6e3a1; color: #11111b; border: none; border-radius: 4px; padding: 2px 8px; cursor: pointer; font-size: 11px; font-weight: bold; }
        .send-ide-btn:hover { background: #94e2d5; }
        pre { background: #11111b; padding: 14px; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; overflow-x: auto; border: 1px solid #181825; margin: 0; }
        code { font-family: 'Ubuntu Mono', monospace; color: #f38ba8; }
        pre code { color: #a6e3a1; }
        .msg-bubble.user code { color: #1e1e2e; background: rgba(255,255,255,0.2); padding: 2px 4px; border-radius: 4px; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        th, td { border: 1px solid #45475a; padding: 8px; }
        th { background-color: #181825; }
        details.think-box { background: #181825; border: 1px solid #45475a; border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; color: #a6adc8; font-size: 12.5px; }
        details.think-box summary { cursor: pointer; font-weight: bold; color: #cba6f7; }
        .markdown-body { margin: 0; }
                .chart-box { background: #11111b; padding: 15px; border-radius: 8px; margin: 12px 0; border: 1px solid #45475a; min-height: 250px; }
        @page { size: A4 portrait; margin: 8mm; }
        @media print {
            body { padding: 0 !important; margin: 0 !important; font-size: 10.5pt !important; background: #ffffff !important; color: #11111b !important; }
            .chat-container { gap: 8px !important; padding: 0 !important; }
            .msg-bubble { max-width: 100% !important; padding: 8px 12px !important; font-size: 10.5pt !important; line-height: 1.35 !important; box-shadow: none !important; border: 1px solid #ccc !important; background: #f8f9fa !important; color: #11111b !important; }
            .msg-bubble.user { background: #e9ecef !important; color: #11111b !important; }
            pre { padding: 8px !important; font-size: 9pt !important; background: #f1f3f5 !important; border: 1px solid #ced4da !important; }
            pre code, code { color: #11111b !important; font-size: 9pt !important; }
            h1 { font-size: 14pt !important; margin: 6px 0 !important; }
            h2 { font-size: 12.5pt !important; margin: 5px 0 !important; }
            h3 { font-size: 11pt !important; margin: 4px 0 !important; }
            .copy-btn, .code-header, details.think-box { display: none !important; }
            .chart-box { min-height: 160px !important; padding: 8px !important; margin: 6px 0 !important; page-break-inside: avoid; }
        }
    </style>
</head>
<body>
    <div class="chat-container" id="chat"></div>
    <script>
        if (typeof mermaid !== 'undefined') {
            mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' });
        }

        function copyContent(btn) {
            var rawText = decodeURIComponent(btn.getAttribute('data-raw'));
            var textArea = document.createElement("textarea");
            textArea.value = rawText;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            var old = btn.innerHTML;
            btn.innerHTML = '✅';
            setTimeout(() => btn.innerHTML = old, 2000);
        }

        function sendToIde(btn) {
            var rawCode = btn.getAttribute('data-raw');
            var lang = btn.getAttribute('data-lang') || 'py';
            window.prompt("MIA_SEND_TO_IDE:" + lang, rawCode);
            var old = btn.innerHTML;
            btn.innerHTML = '✅ Envoyé !';
            setTimeout(() => btn.innerHTML = old, 1500);
        }

        function viewRagSource(badge) {
            var payload = badge.getAttribute('data-source');
            window.prompt("MIA_VIEW_SOURCE:", payload);
        }

        function renderMiaMath(container) {
            if (typeof katex === 'undefined') return;
            container.querySelectorAll('.mia-math').forEach((el) => {
                if (el.getAttribute('data-done') === '1') return;
                el.setAttribute('data-done', '1');
                let tex = decodeURIComponent(el.getAttribute('data-tex') || '');
                let isDisplay = el.getAttribute('data-display') === '1';
                try {
                    katex.render(tex, el, { displayMode: isDisplay, throwOnError: false });
                } catch (e) {
                    el.textContent = tex;
                }
            });
        }

        async function renderVisualsIn(container) {
            renderMiaMath(container);
            const chartDivs = container.querySelectorAll('.mia-chart-target');
            chartDivs.forEach((div) => {
                if (div.getAttribute('data-done') === '1') return;
                div.setAttribute('data-done', '1');
                try {
                    let cfg = JSON.parse(decodeURIComponent(div.getAttribute('data-config')));
                    let canvas = document.createElement('canvas');
                    div.innerHTML = '';
                    div.appendChild(canvas);
                    Chart.defaults.color = '#cdd6f4';
                    Chart.defaults.borderColor = '#313244';
                    new Chart(canvas, cfg);
                } catch (e) {
                    div.innerHTML = `<div style="color:#f38ba8;">Erreur Chart.js : ${e.message}</div>`;
                }
            });

            const mermaidDivs = container.querySelectorAll('.mia-mermaid-target');
            for (let i = 0; i < mermaidDivs.length; i++) {
                let div = mermaidDivs[i];
                if (div.getAttribute('data-done') === '1') continue;
                div.setAttribute('data-done', '1');
                let code = decodeURIComponent(div.getAttribute('data-code'));
                let targetId = 'mmd-' + Date.now() + '-' + Math.floor(Math.random() * 10000);
                try {
                    await mermaid.parse(code);
                    const { svg } = await mermaid.render(targetId, code);
                    div.innerHTML = svg;
                } catch (e) {
                    let errNode = document.getElementById('d' + targetId) || document.getElementById(targetId);
                    if (errNode) errNode.remove();
                    div.style.textAlign = 'left';
                    div.innerHTML = `<div style="color:#fab387;font-size:13px;margin-bottom:6px;">⚠️ Code schéma brut :</div><pre style="margin:0;"><code>${code}</code></pre>`;
                }
            }
        }

        window.updateChat = function(messagesHtml, isGenerating) {
            const chat = document.getElementById('chat');
            for (let i = 0; i < messagesHtml.length; i++) {
                let row = document.getElementById('msg-row-' + i);
                if (!row) {
                    row = document.createElement('div');
                    row.id = 'msg-row-' + i;
                    chat.appendChild(row);
                }
                let isLastAndGenerating = (i === messagesHtml.length - 1) && isGenerating;
                let contentChanged = (row.getAttribute('data-raw') !== messagesHtml[i]);
                let needsFinalRender = (!isLastAndGenerating && row.getAttribute('data-rendered') !== 'true');
                if (contentChanged || needsFinalRender) {
                    row.innerHTML = messagesHtml[i];
                    row.setAttribute('data-raw', messagesHtml[i]);
                    if (typeof renderMathInElement !== 'undefined') {
                        renderMathInElement(row, {
                            delimiters: [
                                {left: "$$", right: "$$", display: true},
                                {left: "\\[", right: "\\]", display: true},
                                {left: "$", right: "$", display: false},
                                {left: "\\(", right: "\\)", display: false}
                            ]
                        });
                    }
                    if (!isLastAndGenerating) {
                        row.setAttribute('data-rendered', 'true');
                        renderVisualsIn(row);
                    } else {
                        row.setAttribute('data-rendered', 'false');
                    }
                }
            }
            while (chat.children.length > messagesHtml.length) {
                chat.removeChild(chat.lastChild);
            }
            window.scrollTo(0, document.body.scrollHeight);
        };
    </script>
</body>
</html>
"""

class BridgeWebPage(QWebEnginePage):
    code_received = pyqtSignal(str, str)
    source_clicked = pyqtSignal(dict)

    def javaScriptPrompt(self, securityOrigin, msg, defaultValue):
        if msg.startswith("MIA_SEND_TO_IDE:"):
            lang = msg.split(":", 1)[1]
            decoded_code = urllib.parse.unquote(defaultValue)
            self.code_received.emit(decoded_code, lang)
            return True, ""
        elif msg.startswith("MIA_VIEW_SOURCE:"):
            try:
                src_data = json.loads(urllib.parse.unquote(defaultValue))
                self.source_clicked.emit(src_data)
            except Exception:
                pass
            return True, ""
        return super().javaScriptPrompt(securityOrigin, msg, defaultValue)

def try_parse_chart_block(lang, raw_body):
    text = raw_body.replace('\u00a0', ' ').strip()
    is_chart_candidate = (
        lang in ('plot', 'chart', 'chartjs') or
        text.lower().startswith('chartjs') or
        ('labels:' in text and 'data:' in text) or
        ('"labels"' in text and '"data"' in text)
    )
    if not is_chart_candidate:
        return None

    clean = re.sub(r'^chartjs\s*', '', text, flags=re.IGNORECASE).strip()

    try:
        cfg = json.loads(clean)
        if isinstance(cfg, dict) and 'data' in cfg:
            if 'options' in cfg and 'scales' in cfg['options']:
                if 'yAxes' in cfg['options']['scales'] or 'xAxes' in cfg['options']['scales']:
                    del cfg['options']['scales']
            return cfg
    except Exception:
        pass

    type_m = re.search(r'type\s*:\s*[\'"]?(line|bar|pie|doughnut|radar|scatter)[\'"]?', clean, re.IGNORECASE)
    labels_m = re.search(r'(?:labels|x)\s*:\s*(\[[^\]]+\])', clean, re.IGNORECASE)
    data_m = re.search(r'(?:data|y)\s*:\s*(\[\s*[-+]?[0-9]*\.?[0-9]+[^\]]*\])', clean, re.IGNORECASE)
    label_m = re.search(r'label\s*:\s*[\'"]?([^\'"\n]+)[\'"]?', clean, re.IGNORECASE)
    color_m = re.search(r'borderColor\s*:\s*[\'"]([^\'"]+)[\'"]', clean, re.IGNORECASE)

    if labels_m and data_m:
        try:
            labels_list = json.loads(labels_m.group(1).replace("'", '"'))
            data_list = json.loads(data_m.group(1))
            c_type = type_m.group(1).lower() if type_m else 'line'
            c_label = label_m.group(1).strip() if label_m else 'Courbe'
            c_color = color_m.group(1).strip() if color_m else '#89b4fa'
            return {
                "type": c_type,
                "data": {
                    "labels": labels_list,
                    "datasets": [{
                        "label": c_label,
                        "data": data_list,
                        "borderColor": c_color,
                        "backgroundColor": "rgba(137, 180, 250, 0.25)",
                        "borderWidth": 2,
                        "tension": 0.35,
                        "fill": (c_type == 'bar')
                    }]
                },
                "options": {"responsive": True}
            }
        except Exception:
            pass
    return None

def format_message_html(content, is_generating=False, rag_sources=None):
    placeholders = {}
    counter = [0]

    def think_replacer(m):
        idx = counter[0]
        counter[0] += 1
        key = f"@@MIATHINK{idx}@@"
        inner = markdown.markdown(m.group(1).strip(), extensions=['nl2br'])
        placeholders[key] = f'<details class="think-box"><summary>🧠 Raisonnement interne (cliquer pour dérouler)</summary><div>{inner}</div></details>'
        return key

    content = re.sub(r'<think>(.*?)</think>', think_replacer, content, flags=re.DOTALL)

    def replacer(match):
        lang = (match.group(1) or '').strip().lower()
        body = match.group(2)
        idx = counter[0]
        counter[0] += 1
        key = f"@@MIABLOCK{idx}@@"

        if not is_generating:
            # Si le LLM a écrit ```latex ou ```math, on le convertit directement en équation KaTeX !
            if lang in ('latex', 'tex', 'math', 'katex'):
                clean_tex = body.strip()
                clean_tex = re.sub(r'^(\$\$|\\[)ert{}(\$\$ert{}\\])$', '', clean_tex).strip()
                enc_tex = urllib.parse.quote(clean_tex)
                placeholders[key] = f'<div class="mia-math" data-display="1" data-tex="{enc_tex}"></div>'
                return key

            chart_cfg = try_parse_chart_block(lang, body)
            if chart_cfg:
                encoded_cfg = urllib.parse.quote(json.dumps(chart_cfg))
                placeholders[key] = f'<div class="chart-box mia-chart-target" data-config="{encoded_cfg}">Chargement du graphique...</div>'
                return key

            if lang == 'mermaid' or re.match(r'^\s*(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|mindmap)\b', body.strip()):
                clean_mmd = body.replace('\u00a0', ' ').strip()
                clean_mmd = re.sub(r'([A-Za-z0-9_]+)\[([^"\]\n]+)\]', r'\1["\2"]', clean_mmd)
                encoded_mmd = urllib.parse.quote(clean_mmd)
                placeholders[key] = f'<div class="chart-box mia-mermaid-target" style="text-align:center;" data-code="{encoded_mmd}">Chargement du schéma...</div>'
                return key

        esc_body = body.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        raw_code_enc = urllib.parse.quote(body.strip())
        lang_label = lang.upper() if lang else "CODE"
        placeholders[key] = (
            f'<div class="code-wrapper">'
            f'<div class="code-header"><span>{lang_label}</span>'
            f'<div class="code-actions">'
            f'<button class="send-ide-btn" data-raw="{raw_code_enc}" data-lang="{lang}" onclick="sendToIde(this)">📥 Vers l\'éditeur</button>'
            f'<button class="copy-code-btn" data-raw="{raw_code_enc}" onclick="copyContent(this)">📋 Copier</button>'
            f'</div></div>'
            f'<pre><code class="language-{lang}">{esc_body}</code></pre></div>'
        )
        return key

    pattern = re.compile(r'```([a-zA-Z0-9_-]*)\s*\n(.*?)```', re.DOTALL)
    safe_text = pattern.sub(replacer, content)

    # Extraction et protection des équations mathématiques AVANT le passage dans Markdown
    if not is_generating:
        def math_block_repl(m):
            idx = counter[0]
            counter[0] += 1
            key = f"@@MIAMATH{idx}@@"
            tex = (m.group(1) if m.group(1) is not None else m.group(2)).strip()
            enc_tex = urllib.parse.quote(tex)
            placeholders[key] = f'<div class="mia-math" data-display="1" data-tex="{enc_tex}"></div>'
            return key

        def math_inline_repl(m):
            idx = counter[0]
            counter[0] += 1
            key = f"@@MIAMATH{idx}@@"
            tex = (m.group(1) if m.group(1) is not None else m.group(2)).strip()
            enc_tex = urllib.parse.quote(tex)
            placeholders[key] = f'<span class="mia-math" data-display="0" data-tex="{enc_tex}"></span>'
            return key

        # Blocs $$...$$ et \[...\]
        safe_text = re.sub(r'\$\$(.+?)\$\$|\\\[(.+?)\\\]', math_block_repl, safe_text, flags=re.DOTALL)
        # Inline \(...\) et $...$ (sans traverser les sauts de ligne)
        safe_text = re.sub(r'\\\((.+?)\\\)|(?<!\$)\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\$)', math_inline_repl, safe_text)

    md_html = markdown.markdown(safe_text, extensions=['fenced_code', 'tables', 'nl2br'])

    for key, html_val in placeholders.items():
        md_html = md_html.replace(key, html_val)

    if rag_sources:
        badges_html = '<div class="rag-badges">'
        for s in rag_sources:
            enc_s = urllib.parse.quote(json.dumps(s))
            badges_html += f'<span class="rag-badge" data-source="{enc_s}" onclick="viewRagSource(this)" title="Cliquer pour inspecter la source">📖 {s.get("label", "Source")}</span>'
        badges_html += '</div>'
        md_html = badges_html + md_html

    return md_html

def convert_markdown_to_dokuwiki(text):
    lines = text.splitlines()
    out = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip()
            if not in_code:
                out.append(f"<code {lang}>" if lang else "<code>")
                in_code = True
            else:
                out.append("</code>")
                in_code = False
            continue
        if in_code:
            out.append(line)
            continue

        if re.match(r'^\s*[-*_]{3,}\s*$', line):
            out.append("----")
            continue

        m_h = re.match(r'^(#{1,5})\s+(.*)$', line)
        if m_h:
            level = 7 - len(m_h.group(1))
            eq = "=" * max(2, level)
            out.append(f"{eq} {m_h.group(2).strip()} {eq}")
            continue

        m_ul = re.match(r'^(\s*)[-*+]\s+(.*)$', line)
        if m_ul:
            depth = max(1, (len(m_ul.group(1)) // 2) + 1)
            line = ("    " * depth) + "* " + m_ul.group(2)

        line = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'[[\2|\1]]', line)
        line = re.sub(r'(?<!http)(?<!https):\s+([A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ])', lambda m: ": " + m.group(1).lower(), line)
        out.append(line)
    return "\n".join(out)

def build_inline_katex_assets():
    """Lit katex.min.css, encode les polices woff2 en base64 (avec ou sans quotes) et retourne CSS + JS."""
    katex_dir = os.path.join(APP_DIR, "katex")
    css_path = os.path.join(katex_dir, "katex.min.css")
    js_path = os.path.join(katex_dir, "katex.min.js")
    auto_path = os.path.join(katex_dir, "contrib", "auto-render.min.js")

    css_content = ""
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8", errors="ignore") as f:
            css_content = f.read()

        def embed_font(match):
            rel_font = match.group(1).strip("'\" ")
            font_file = os.path.join(katex_dir, rel_font)
            if os.path.exists(font_file):
                with open(font_file, "rb") as bf:
                    b64 = base64.b64encode(bf.read()).decode("ascii")
                mime = "font/woff2" if rel_font.endswith(".woff2") else ("font/woff" if rel_font.endswith(".woff") else "font/ttf")
                return f'url("data:{mime};base64,{b64}")'
            return match.group(0)

        css_content = re.sub(r"""url\(['"]?(fonts/[^)'"]+)['"]?\)""", embed_font, css_content)

    js_content = ""
    if os.path.exists(js_path):
        with open(js_path, "r", encoding="utf-8", errors="ignore") as f:
            js_content += f.read() + "\n"
    if os.path.exists(auto_path):
        with open(auto_path, "r", encoding="utf-8", errors="ignore") as f:
            js_content += f.read() + "\n"

    return css_content, js_content.replace('</script>', '<\\/script>')

def generate_slides_html(messages):
    """Génère un diaporama HTML autonome avec équations KaTeX garanties et impression PDF aux marges/polices calibrées."""
    raw_md = "\n\n---\n\n".join([m['content'] for m in messages if m['role'] == 'assistant'])
    raw_md = re.sub(r'<think>.*?</think>', '', raw_md, flags=re.DOTALL)

    slides_raw = []
    current_lines = []
    in_fence = False
    for line in raw_md.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and (re.match(r'^\s*---\s*$', line) or re.match(r'^##\s+', line)):
            if current_lines and "".join(current_lines).strip():
                slides_raw.append("\n".join(current_lines))
            current_lines = [] if re.match(r'^\s*---\s*$', line) else [line]
        else:
            current_lines.append(line)
    if current_lines and "".join(current_lines).strip():
        slides_raw.append("\n".join(current_lines))

    slides_html = []
    for s in slides_raw:
        if not s.strip(): continue
        slide_body = format_message_html(s.strip(), is_generating=False)
        slides_html.append(f'<div class="slide">{slide_body}</div>')

    katex_css, katex_js = build_inline_katex_assets()
    mermaid_path = os.path.join(APP_DIR, "mermaid", "mermaid.min.js")
    chart_path = os.path.join(APP_DIR, "chartjs", "chart.min.js")

    mermaid_inline = ""
    chart_inline = ""
    if os.path.exists(mermaid_path):
        with open(mermaid_path, 'r', encoding='utf-8', errors='ignore') as f:
            mermaid_inline = f.read().replace('</script>', '<\\/script>')
    if os.path.exists(chart_path):
        with open(chart_path, 'r', encoding='utf-8', errors='ignore') as f:
            chart_inline = f.read().replace('</script>', '<\\/script>')

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Présentation MIA</title>
<style>{katex_css}</style>
<script>{katex_js}</script>
<script>{mermaid_inline}</script>
<script>{chart_inline}</script>
<style>
body {{ margin:0; background:#11111b; color:#cdd6f4; font-family:'Ubuntu',sans-serif; overflow:hidden; }}
.slide {{ display:none; box-sizing:border-box; width:100vw; height:100vh; padding:32px 48px 65px 48px; font-size:19px; line-height:1.48; overflow-y:auto; }}
.slide.active {{ display:block; }}
h1 {{ font-size:26px; color:#89b4fa; border-bottom:2px solid #313244; padding-bottom:8px; margin-top:0; }}
h2 {{ font-size:23px; color:#89b4fa; border-bottom:2px solid #313244; padding-bottom:6px; margin-top:0; }}
h3 {{ font-size:19px; color:#89b4fa; margin-top:10px; }}
pre {{ background:#181825; padding:12px 16px; border-radius:8px; font-size:14.5px; border:1px solid #45475a; overflow-x:auto; margin:10px 0; }}
code {{ color:#a6e3a1; font-family:'Ubuntu Mono',monospace; font-size:0.9em; }}
table {{ border-collapse:collapse; width:100%; margin:12px 0; font-size:16px; }}
th, td {{ border:1px solid #45475a; padding:7px 10px; }}
th {{ background:#181825; color:#89b4fa; }}
.mia-math[data-display="1"] {{ margin:14px 0; padding:10px 14px; background:#181825; border-radius:8px; border:1px solid #313244; text-align:center; overflow-x:auto; }}
.katex {{ font-size:1.12em !important; color:#f9e2af; }}
.chart-box {{ background:#181825; padding:15px; border-radius:10px; margin:14px auto; border:1px solid #45475a; width:82%; max-width:820px; min-height:290px; display:flex; align-items:center; justify-content:center; }}
.chart-box canvas {{ width:100% !important; max-height:310px !important; }}
.copy-code-btn, .send-ide-btn, .code-header, details.think-box {{ display:none !important; }}
.controls {{ position:fixed; bottom:16px; right:24px; display:flex; gap:10px; align-items:center; background:#1e1e2e; padding:6px 14px; border-radius:20px; border:1px solid #45475a; font-size:14px; z-index:100; }}
button {{ background:#89b4fa; color:#11111b; border:none; border-radius:6px; padding:5px 11px; font-weight:bold; cursor:pointer; }}

/* CALIBRAGE IMPRESSION PDF : Police 11pt et marges fines de 7mm */
@page {{ size: A4 landscape; margin: 7mm; }}
@media print {{
    body {{ overflow:visible !important; background:#11111b !important; color:#cdd6f4 !important; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
    .slide {{
        display:block !important;
        width:100% !important;
        height:auto !important;
        min-height:0 !important;
        padding:6mm 8mm !important;
        margin:0 !important;
        font-size:11pt !important;
        line-height:1.35 !important;
        page-break-after:always;
        break-after:page;
        overflow:visible !important;
    }}
    .slide:last-of-type {{ page-break-after:auto; break-after:auto; }}
    h1 {{ font-size:15pt !important; margin-bottom:6px !important; padding-bottom:4px !important; }}
    h2 {{ font-size:13.5pt !important; margin-bottom:6px !important; padding-bottom:4px !important; }}
    h3 {{ font-size:11.5pt !important; margin-bottom:4px !important; }}
    p, li {{ font-size:11pt !important; margin:4px 0 !important; }}
    pre {{ font-size:9pt !important; padding:8px !important; margin:6px 0 !important; page-break-inside:avoid; }}
    table {{ font-size:9.5pt !important; margin:6px 0 !important; page-break-inside:avoid; }}
    th, td {{ padding:4px 6px !important; }}
    .mia-math[data-display="1"] {{ margin:8px 0 !important; padding:6px !important; page-break-inside:avoid; }}
    .katex {{ font-size:1.05em !important; }}
    .chart-box {{ width:75% !important; max-width:620px !important; min-height:180px !important; max-height:220px !important; padding:8px !important; margin:8px auto !important; page-break-inside:avoid; }}
    .chart-box canvas {{ max-height:200px !important; }}
    .controls {{ display:none !important; }}
}}
</style>
</head>
<body>
{''.join(slides_html)}
<div class="controls">
    <button onclick="prev()">◀ Préc.</button>
    <span id="counter">1 / {len(slides_html)}</span>
    <button onclick="next()">Suiv. ▶</button>
    <button onclick="prepareAndPrint()" style="background:#a6e3a1;">🖨️ PDF</button>
</div>
<script>
let idx = 0;
const slides = document.querySelectorAll('.slide');

async function renderSlideVisuals(slideEl) {{
    if (!slideEl) return;

    // 1. Rendu direct des conteneurs .mia-math via katex.render()
    if (typeof katex !== 'undefined') {{
        slideEl.querySelectorAll('.mia-math').forEach((el) => {{
            if (el.getAttribute('data-done') === '1') return;
            el.setAttribute('data-done', '1');
            let tex = decodeURIComponent(el.getAttribute('data-tex') || '');
            let isDisplay = el.getAttribute('data-display') === '1';
            try {{
                katex.render(tex, el, {{ displayMode: isDisplay, throwOnError: false }});
            }} catch (e) {{
                el.textContent = tex;
            }}
        }});
    }}

    // 2. Rendu Chart.js
    const chartDivs = slideEl.querySelectorAll('.mia-chart-target');
    chartDivs.forEach((div) => {{
        if (div.getAttribute('data-done') === '1') return;
        div.setAttribute('data-done', '1');
        try {{
            let cfg = JSON.parse(decodeURIComponent(div.getAttribute('data-config')));
            cfg.options = cfg.options || {{}};
            cfg.options.responsive = true;
            cfg.options.maintainAspectRatio = false;
            let canvas = document.createElement('canvas');
            canvas.style.height = '280px';
            div.innerHTML = '';
            div.appendChild(canvas);
            Chart.defaults.color = '#cdd6f4';
            Chart.defaults.borderColor = '#313244';
            new Chart(canvas, cfg);
        }} catch (e) {{
            div.innerHTML = '<div style="color:#f38ba8;">Erreur graphique : ' + e.message + '</div>';
        }}
    }});

    // 3. Rendu Mermaid
    const mermaidDivs = slideEl.querySelectorAll('.mia-mermaid-target');
    for (let i = 0; i < mermaidDivs.length; i++) {{
        let div = mermaidDivs[i];
        if (div.getAttribute('data-done') === '1') continue;
        div.setAttribute('data-done', '1');
        let code = decodeURIComponent(div.getAttribute('data-code'));
        let targetId = 'mmd-slide-' + Date.now() + '-' + Math.floor(Math.random() * 10000);
        try {{
            await mermaid.parse(code);
            const {{ svg }} = await mermaid.render(targetId, code);
            div.innerHTML = svg;
        }} catch (e) {{
            div.innerHTML = '<pre style="text-align:left;color:#fab387;">' + code + '</pre>';
        }}
    }}
}}

// Pré-rend toutes les diapositives avant d'ouvrir la boîte d'impression PDF
async function prepareAndPrint() {{
    for (let i = 0; i < slides.length; i++) {{
        slides[i].style.display = 'block';
        await renderSlideVisuals(slides[i]);
    }}
    setTimeout(() => {{
        window.print();
        for (let i = 0; i < slides.length; i++) {{
            slides[i].style.display = '';
        }}
    }}, 350);
}}

function show(n) {{
    if(slides.length === 0) return;
    slides[idx].classList.remove('active');
    idx = (n + slides.length) % slides.length;
    slides[idx].classList.add('active');
    document.getElementById('counter').textContent = (idx+1) + ' / ' + slides.length;
    setTimeout(() => renderSlideVisuals(slides[idx]), 50);
}}
function next() {{ show(idx + 1); }}
function prev() {{ show(idx - 1); }}

window.addEventListener('DOMContentLoaded', async () => {{
    if (typeof mermaid !== 'undefined') {{
        mermaid.initialize({{ startOnLoad: false, theme: 'dark', securityLevel: 'loose' }});
    }}
    // Rendu immédiat de toutes les équations mathématiques de toutes les slides dès le chargement
    for (let i = 0; i < slides.length; i++) {{
        if (typeof katex !== 'undefined') {{
            slides[i].querySelectorAll('.mia-math').forEach((el) => {{
                let tex = decodeURIComponent(el.getAttribute('data-tex') || '');
                let isDisplay = el.getAttribute('data-display') === '1';
                try {{
                    katex.render(tex, el, {{ displayMode: isDisplay, throwOnError: false }});
                    el.setAttribute('data-done', '1');
                }} catch (e) {{}}
            }});
        }}
    }}
    if(slides.length > 0) {{
        slides[0].classList.add('active');
        setTimeout(() => renderSlideVisuals(slides[0]), 60);
    }}
}});

document.addEventListener('keydown', e => {{
    if(e.key === 'ArrowRight' || e.key === ' ') next();
    if(e.key === 'ArrowLeft') prev();
}});
</script>
</body>
</html>"""

def extract_moodle_gift(messages):
    full_text = "\n\n".join([m['content'] for m in messages if m['role'] == 'assistant'])
    gift_blocks = re.findall(r'```(?:gift)?\n(.*?::.*?)```', full_text, flags=re.DOTALL | re.IGNORECASE)
    if gift_blocks:
        return "\n\n".join(b.strip() for b in gift_blocks)
    return full_text

class LatexEditorDialog(QDialog):
    """Éditeur visuel d'équations LaTeX avec aperçu KaTeX en temps réel."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("∑ Éditeur d'Équations Mathématiques (LaTeX / KaTeX)")
        self.resize(680, 420)
        layout = QVBoxLayout(self)

        lbl_models = QLabel("Symboles & Modèles rapides (cliquer pour insérer) :")
        layout.addWidget(lbl_models)

        sym_bar = QHBoxLayout()
        presets = [
            ("Fraction", r"\frac{a}{b}"),
            ("Racine", r"\sqrt{x}"),
            ("Somme ∑", r"\sum_{i=1}^{n} x_i"),
            ("Intégrale ∫", r"\int_{-\infty}^{+\infty} f(x)\,dx"),
            ("Gaussienne", r"f(x) = \frac{1}{\sigma\sqrt{2\pi}} e^{-\frac{1}{2}\left(\frac{x-\mu}{\sigma}\right)^2}"),
            ("Matrice 2x2", r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}"),
            ("RSA", r"c \equiv m^e \pmod{n}")
        ]
        for label, tex in presets:
            b = QPushButton(label)
            b.setStyleSheet("font-size: 11.5px; padding: 4px 8px;")
            b.clicked.connect(lambda _, t=tex: self.insert_tex(t))
            sym_bar.addWidget(b)
        layout.addLayout(sym_bar)

        self.input_tex = QTextEdit()
        self.input_tex.setMaximumHeight(95)
        self.input_tex.setPlainText(r"f(x) = \frac{1}{\sigma\sqrt{2\pi}} e^{-\frac{1}{2}\left(\frac{x-\mu}{\sigma}\right)^2}")
        self.input_tex.textChanged.connect(self.update_preview)
        layout.addWidget(self.input_tex)

        layout.addWidget(QLabel("Aperçu en direct :"))
        self.preview = QWebEngineView()
        self.preview.setMinimumHeight(140)
        layout.addWidget(self.preview)

        btns = QHBoxLayout()
        btn_insert_block = QPushButton("➕ Insérer en bloc centré ($$ ... $$)")
        btn_insert_block.setStyleSheet("background-color: #a6e3a1; color: #11111b; border: none;")
        btn_insert_block.clicked.connect(lambda: self.done(1))

        btn_insert_inline = QPushButton("➕ Insérer dans la phrase ($ ... $)")
        btn_insert_inline.setStyleSheet("background-color: #89b4fa; color: #11111b; border: none;")
        btn_insert_inline.clicked.connect(lambda: self.done(2))

        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self.reject)

        btns.addWidget(btn_insert_block)
        btns.addWidget(btn_insert_inline)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)
        self.update_preview()

    def insert_tex(self, tex):
        self.input_tex.insertPlainText(tex)
        self.input_tex.setFocus()

    def update_preview(self):
        tex = self.input_tex.toPlainText().strip()
        html = f"""<!DOCTYPE html><html><head>
        <link rel="stylesheet" href="katex/katex.min.css">
        <script src="katex/katex.min.js"></script>
        <style>body {{ background:#11111b; color:#f9e2af; display:flex; align-items:center; justify-content:center; height:85vh; margin:0; font-size:22px; }}</style>
        </head><body><div id="math"></div>
        <script>
        try {{ katex.render({json.dumps(tex)}, document.getElementById('math'), {{displayMode: true, throwOnError: false}}); }}
        catch(e) {{ document.getElementById('math').innerText = e.message; }}
        </script></body></html>"""
        self.preview.setHtml(html, QUrl.fromLocalFile(APP_DIR + "/"))

class DiffDialog(QDialog):
    def __init__(self, old_code, new_code, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Comparaison des modifications (Mode Diff)")
        self.resize(820, 560)
        layout = QVBoxLayout(self)

        lbl = QLabel("Vérifiez les lignes ajoutées (vert) et supprimées (rouge) avant d'appliquer :")
        layout.addWidget(lbl)

        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        diff_lines = list(difflib.unified_diff(
            old_code.splitlines(), new_code.splitlines(),
            fromfile="Code actuel", tofile="Code proposé par MIA", lineterm=""
        ))
        html_lines = []
        for line in diff_lines:
            esc = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            if line.startswith('+') and not line.startswith('+++'):
                html_lines.append(f'<div style="background:#1e3a2f;color:#a6e3a1;">{esc}</div>')
            elif line.startswith('-') and not line.startswith('---'):
                html_lines.append(f'<div style="background:#3a1e28;color:#f38ba8;">{esc}</div>')
            elif line.startswith('@@'):
                html_lines.append(f'<div style="color:#89b4fa;font-weight:bold;">{esc}</div>')
            else:
                html_lines.append(f'<div>{esc}</div>')
        if not html_lines:
            html_lines.append('<div>Aucune différence détectée.</div>')
        self.viewer.setHtml(f'<pre style="font-family:\'Ubuntu Mono\',monospace;font-size:13px;">{"".join(html_lines)}</pre>')
        layout.addWidget(self.viewer)

        btn_layout = QHBoxLayout()
        btn_apply = QPushButton("✅ Remplacer dans l'onglet actif")
        btn_apply.setStyleSheet("background-color: #a6e3a1; color: #11111b; border: none;")
        btn_apply.clicked.connect(lambda: self.done(1))

        btn_new_tab = QPushButton("📄 Ouvrir dans un nouvel onglet")
        btn_new_tab.clicked.connect(lambda: self.done(2))

        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_new_tab)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

class SourceViewerDialog(QDialog):
    def __init__(self, src_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📖 Source : {src_data.get('label', 'Document')}")
        self.resize(680, 440)
        layout = QVBoxLayout(self)

        path_lbl = QLabel(f"Fichier : {src_data.get('path', 'Inconnu')} (Page {src_data.get('page', '?')})")
        path_lbl.setStyleSheet("color: #89b4fa; font-weight: bold;")
        layout.addWidget(path_lbl)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(src_data.get("snippet", ""))
        layout.addWidget(txt)

        btn_layout = QHBoxLayout()
        filepath = src_data.get("path", "")
        if filepath and os.path.exists(filepath):
            btn_open = QPushButton("📂 Ouvrir le fichier original sur le système")
            btn_open.setStyleSheet("background-color: #a6e3a1; color: #11111b; border: none;")
            btn_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(filepath)))
            btn_layout.addWidget(btn_open)

        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

class BatchGraderWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)

    def __init__(self, folder, rubric, model, ollama_url):
        super().__init__()
        self.folder, self.rubric, self.model, self.ollama_url = folder, rubric, model, ollama_url.rstrip('/')

    def run(self):
        from pypdf import PdfReader
        valid_exts = ('.pdf', '.py', '.sh', '.txt', '.md')
        files = [f for f in sorted(os.listdir(self.folder)) if f.lower().endswith(valid_exts)]
        if not files:
            self.finished_signal.emit("⚠️ Aucun fichier étudiant (.pdf, .py, .sh, .txt, .md) trouvé dans ce dossier.")
            return

        report = [f"# 🎓 Rapport d'Évaluation par Lot\n*Date : {datetime.now().strftime('%Y-%m-%d %H:%M')} — Modèle : {self.model}*\n"]
        for idx, fname in enumerate(files, 1):
            self.progress_signal.emit(f"Évaluation ({idx}/{len(files)}) : {fname}...")
            fpath = os.path.join(self.folder, fname)
            content = ""
            try:
                if fname.lower().endswith('.pdf'):
                    reader = PdfReader(fpath)
                    content = "\n".join((p.extract_text() or "") for p in reader.pages)
                else:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
            except Exception as e:
                report.append(f"## 📄 {fname}\n❌ Erreur de lecture : {e}\n")
                continue

            prompt = (
                f"Tu es directeur de formation et correcteur académique.\n"
                f"BARÈME ET CRITÈRES D'ÉVALUATION :\n{self.rubric}\n\n"
                f"COPIE / CODE DE L'ÉTUDIANT ({fname}) :\n```\n{content[:12000]}\n```\n\n"
                f"Fournis une évaluation structurée contenant : Points forts, Points à corriger, Note proposée selon le barème et Appréciation constructive."
            )
            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}},
                    timeout=180
                )
                ans = resp.json().get("response", "Pas de réponse.")
                ans = re.sub(r'<think>.*?</think>', '', ans, flags=re.DOTALL).strip()
                report.append(f"## 📄 Étudiant / Fichier : `{fname}`\n\n{ans}\n\n---\n")
            except Exception as e:
                report.append(f"## 📄 `{fname}`\n❌ Erreur Ollama : {e}\n\n---\n")

        self.finished_signal.emit("\n".join(report))

class BatchGraderDialog(QDialog):
    def __init__(self, model, ollama_url, parent=None):
        super().__init__(parent)
        self.model, self.ollama_url = model, ollama_url
        self.setWindowTitle("🎓 Correcteur de Copies / TP par Lot")
        self.resize(760, 580)
        layout = QVBoxLayout(self)

        dir_layout = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("Sélectionnez le dossier contenant les fichiers des étudiants (.pdf, .py, .sh, .md)...")
        btn_browse = QPushButton("📂 Parcourir")
        btn_browse.clicked.connect(self.choose_dir)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(btn_browse)
        layout.addLayout(dir_layout)

        layout.addWidget(QLabel("Grille d'évaluation / Barème / Attendus pédagogiques :"))
        self.rubric_edit = QTextEdit()
        self.rubric_edit.setMaximumHeight(120)
        self.rubric_edit.setPlainText(
            "Barème sur 20 points :\n"
            "- Fonctionnalité et respect des consignes : /8\n"
            "- Qualité technique, sécurité et gestion des erreurs : /6\n"
            "- Clarté, structuration et commentaires : /6"
        )
        layout.addWidget(self.rubric_edit)

        btn_run = QPushButton("🚀 Lancer l'évaluation automatisée du dossier")
        btn_run.setStyleSheet("background-color: #89b4fa; color: #11111b; border: none;")
        btn_run.clicked.connect(self.start_grading)
        layout.addWidget(btn_run)

        self.lbl_status = QLabel("Prêt.")
        self.lbl_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        layout.addWidget(self.lbl_status)

        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        layout.addWidget(self.result_view)

        btn_save = QPushButton("💾 Enregistrer le rapport d'évaluation (.md)")
        btn_save.clicked.connect(self.save_report)
        layout.addWidget(btn_save)

    def choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Dossier des copies / TP")
        if d: self.dir_edit.setText(d)

    def start_grading(self):
        folder = self.dir_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Dossier requis", "Veuillez sélectionner un dossier valide.")
            return
        self.worker = BatchGraderWorker(folder, self.rubric_edit.toPlainText(), self.model, self.ollama_url)
        self.worker.progress_signal.connect(self.lbl_status.setText)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, report_md):
        self.lbl_status.setText("✅ Évaluation du lot terminée !")
        self.result_view.setPlainText(report_md)

    def save_report(self):
        if not self.result_view.toPlainText().strip(): return
        p, _ = QFileDialog.getSaveFileName(self, "Sauvegarder le rapport", "rapport_evaluation.md", "Markdown (*.md)")
        if p:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(self.result_view.toPlainText())

class CodeEditorTab(QsciScintilla):
    ask_ai_selection = pyqtSignal(str, str)

    def __init__(self, filepath=None, ext="py", parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.ext = ext.lower().lstrip('.')
        self.setUtf8(True)

        font = QFont("Ubuntu Mono", 11)
        self.setFont(font)
        self.setMarginsFont(font)

        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "0000")
        self.setMarginsForegroundColor(QColor("#6c7086"))
        self.setMarginsBackgroundColor(QColor("#181825"))

        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)
        self.setFoldMarginColors(QColor("#181825"), QColor("#181825"))

        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setAutoIndent(True)
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#1e1e2e"))
        self.setCaretForegroundColor(QColor("#89b4fa"))

        self.setSelectionBackgroundColor(QColor("#45475a"))
        self.setSelectionForegroundColor(QColor("#cdd6f4"))

        self.apply_lexer(self.ext, font)

    def apply_lexer(self, ext, font):
        lexer_map = {
            'py': QsciLexerPython,
            'sh': QsciLexerBash,
            'bash': QsciLexerBash,
            'json': QsciLexerJSON,
            'yml': QsciLexerYAML,
            'yaml': QsciLexerYAML,
            'md': QsciLexerMarkdown,
            'sql': QsciLexerSQL
        }
        lexer_cls = lexer_map.get(ext)
        if lexer_cls:
            lexer = lexer_cls(self)
            lexer.setDefaultFont(font)
            lexer.setDefaultPaper(QColor("#11111b"))
            lexer.setDefaultColor(QColor("#cdd6f4"))
            for style in range(128):
                lexer.setPaper(QColor("#11111b"), style)
                lexer.setFont(font, style)
            self.setLexer(lexer)
        else:
            self.setPaper(QColor("#11111b"))
            self.setColor(QColor("#cdd6f4"))

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        if self.hasSelectedText():
            menu.addSeparator()
            act_fix = QAction("🛠️ Demander à l'IA de corriger / optimiser cette sélection", self)
            act_fix.triggered.connect(lambda: self.ask_ai_selection.emit(self.selectedText(), self.ext))
            menu.addAction(act_fix)
            act_rb = QAction("⚔️ Soumettre cette sélection au Conseil Cyber (Red vs Blue)", self)
            act_rb.triggered.connect(lambda: self.ask_ai_selection.emit("@@COUNCIL@@" + self.selectedText(), self.ext))
            menu.addAction(act_rb)
        menu.exec(event.globalPos())

class CodeStudioWidget(QWidget):
    send_to_chat_signal = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project_dir = os.path.expanduser("~")
        self.last_error_output = ""
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 0, 0, 0)

        # Barre d'outils compacte (évite tout élargissement forcé de la fenêtre)
        toolbar = QHBoxLayout()
        btn_open_dir = QPushButton("📂 Projet")
        btn_open_dir.clicked.connect(self.choose_project_dir)
        toolbar.addWidget(btn_open_dir)

        btn_new_file = QPushButton("📄 Nouveau")
        btn_new_file.clicked.connect(self.create_empty_tab)
        toolbar.addWidget(btn_new_file)

        btn_save = QPushButton("💾 Sauver")
        btn_save.setStyleSheet("background-color: #a6e3a1; color: #11111b; border: none;")
        btn_save.clicked.connect(self.save_current_tab)
        toolbar.addWidget(btn_save)

        btn_lint = QPushButton("✅ Syntaxe")
        btn_lint.clicked.connect(self.lint_current_tab)
        toolbar.addWidget(btn_lint)

        btn_run = QPushButton("▶️ Exécuter")
        btn_run.setStyleSheet("background-color: #89b4fa; color: #11111b; border: none;")
        btn_run.clicked.connect(self.run_current_tab)
        toolbar.addWidget(btn_run)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.save_current_tab)

        v_split = QSplitter(Qt.Orientation.Vertical)
        h_split = QSplitter(Qt.Orientation.Horizontal)

        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_proj = QLabel("📁 ~")
        self.lbl_proj.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 12px;")
        tree_layout.addWidget(self.lbl_proj)

        self.fs_model = QFileSystemModel()
        self.fs_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
        self.fs_model.setRootPath(self.current_project_dir)

        self.tree = QTreeView()
        self.tree.setModel(self.fs_model)
        self.tree.setRootIndex(self.fs_model.index(self.current_project_dir))
        for col in (1, 2, 3):
            self.tree.hideColumn(col)
        self.tree.setHeaderHidden(True)
        self.tree.doubleClicked.connect(self.on_tree_double_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_tree_menu)
        tree_layout.addWidget(self.tree)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        h_split.addWidget(tree_container)
        h_split.addWidget(self.tabs)
        h_split.setSizes([160, 420])

        console_container = QWidget()
        console_layout = QVBoxLayout(console_container)
        console_layout.setContentsMargins(0, 0, 0, 0)

        # Barre Console + Outils Git regroupés au-dessus de la console
        con_header = QHBoxLayout()
        lbl_con = QLabel("🖥️ Console :")
        lbl_con.setStyleSheet("color: #a6adc8; font-size: 12px; font-weight: bold;")
        con_header.addWidget(lbl_con)

        btn_git_status = QPushButton("📊 Git Status")
        btn_git_status.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        btn_git_status.clicked.connect(self.git_status)
        con_header.addWidget(btn_git_status)

        btn_git_diff = QPushButton("🔍 Git Diff")
        btn_git_diff.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        btn_git_diff.clicked.connect(self.git_diff)
        con_header.addWidget(btn_git_diff)

        btn_git_commit = QPushButton("✨ Commit IA")
        btn_git_commit.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        btn_git_commit.clicked.connect(self.git_commit_ai)
        con_header.addWidget(btn_git_commit)

        con_header.addStretch()

        self.btn_fix_err = QPushButton("🔧 Corriger l'erreur via IA")
        self.btn_fix_err.setStyleSheet("background-color: #fab387; color: #11111b; border: none; font-size: 11px; padding: 3px 8px;")
        self.btn_fix_err.clicked.connect(self.send_error_to_ai)
        self.btn_fix_err.hide()
        con_header.addWidget(self.btn_fix_err)
        console_layout.addLayout(con_header)

        self.console_out = QTextEdit()
        self.console_out.setReadOnly(True)
        self.console_out.setStyleSheet("font-family: 'Ubuntu Mono', monospace; font-size: 12px; background-color: #11111b; color: #a6e3a1;")
        console_layout.addWidget(self.console_out)

        v_split.addWidget(h_split)
        v_split.addWidget(console_container)
        v_split.setSizes([520, 140])
        layout.addWidget(v_split)

        self.create_empty_tab()

    def choose_project_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Ouvrir un dossier de projet", self.current_project_dir)
        if folder:
            self.current_project_dir = folder
            self.lbl_proj.setText(f"📁 {os.path.basename(folder)}")
            self.fs_model.setRootPath(folder)
            self.tree.setRootIndex(self.fs_model.index(folder))

    def on_tree_double_clicked(self, index):
        path = self.fs_model.filePath(index)
        if os.path.isfile(path):
            self.open_file_in_tab(path)

    def show_tree_menu(self, pos):
        index = self.tree.indexAt(pos)
        target_path = self.fs_model.filePath(index) if index.isValid() else self.current_project_dir
        base_dir = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)

        menu = QMenu(self)
        act_new_f = QAction("📄 Nouveau fichier ici", self)
        act_new_d = QAction("📁 Nouveau dossier ici", self)
        menu.addAction(act_new_f)
        menu.addAction(act_new_d)

        act_send_ai = None
        act_send_tree = QAction("🌳 Envoyer l'arborescence du projet à l'IA", self)
        menu.addAction(act_send_tree)

        act_del = None
        if index.isValid() and os.path.isfile(target_path):
            menu.addSeparator()
            act_send_ai = QAction("🧠 Envoyer ce fichier à l'IA comme contexte", self)
            menu.addAction(act_send_ai)

        if index.isValid():
            menu.addSeparator()
            act_del = QAction("🗑️ Supprimer", self)
            menu.addAction(act_del)

        chosen = menu.exec(self.tree.mapToGlobal(pos))
        if not chosen: return

        if chosen == act_new_f:
            name, ok = QInputDialog.getText(self, "Nouveau fichier", "Nom du fichier (ex: script.py) :")
            if ok and name.strip():
                new_p = os.path.join(base_dir, name.strip())
                open(new_p, 'a', encoding='utf-8').close()
                self.open_file_in_tab(new_p)
        elif chosen == act_new_d:
            name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom du dossier :")
            if ok and name.strip():
                os.makedirs(os.path.join(base_dir, name.strip()), exist_ok=True)
        elif chosen == act_send_tree:
            tree_str = self.generate_tree_summary(self.current_project_dir)
            self.send_to_chat_signal.emit(f"\nVoici l'arborescence de mon projet `{os.path.basename(self.current_project_dir)}` :\n```text\n{tree_str}\n```\n", False)
        elif act_send_ai and chosen == act_send_ai:
            with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                ext = os.path.splitext(target_path)[1].lstrip('.')
                self.send_to_chat_signal.emit(f"\nVoici le fichier `{os.path.basename(target_path)}` :\n```{ext}\n{f.read()}\n```\n", False)
        elif act_del and chosen == act_del:
            if QMessageBox.question(self, "Confirmer", f"Supprimer {os.path.basename(target_path)} ?") == QMessageBox.StandardButton.Yes:
                if os.path.isdir(target_path): shutil.rmtree(target_path)
                else: os.remove(target_path)

    def generate_tree_summary(self, root_dir, max_entries=80):
        lines = []
        count = 0
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', '__pycache__', 'node_modules')]
            rel = os.path.relpath(root, root_dir)
            depth = 0 if rel == '.' else rel.count(os.sep) + 1
            indent = "  " * depth
            if rel != '.':
                lines.append(f"{indent}📁 {os.path.basename(root)}/")
            for f in sorted(files):
                if f.startswith('.'): continue
                lines.append(f"{indent}  📄 {f}")
                count += 1
                if count >= max_entries:
                    lines.append("  ... (tronqué)")
                    return "\n".join(lines)
        return "\n".join(lines)

    def open_file_in_tab(self, filepath):
        for i in range(self.tabs.count()):
            ed = self.tabs.widget(i)
            if ed.filepath == filepath:
                self.tabs.setCurrentIndex(i)
                return

        ext = os.path.splitext(filepath)[1].lstrip('.') or 'py'
        editor = CodeEditorTab(filepath=filepath, ext=ext, parent=self)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            editor.setText(f.read())
        editor.setModified(False)
        editor.modificationChanged.connect(lambda m, ed=editor: self.update_tab_title(ed, m))
        editor.ask_ai_selection.connect(self.on_ask_ai_selection)

        idx = self.tabs.addTab(editor, os.path.basename(filepath))
        self.tabs.setCurrentIndex(idx)

    def create_empty_tab(self, code="", ext="py"):
        editor = CodeEditorTab(filepath=None, ext=ext, parent=self)
        if code:
            editor.setText(code)
        editor.modificationChanged.connect(lambda m, ed=editor: self.update_tab_title(ed, m))
        editor.ask_ai_selection.connect(self.on_ask_ai_selection)
        idx = self.tabs.addTab(editor, f"brouillon.{ext}")
        self.tabs.setCurrentIndex(idx)

    def receive_code_from_chat(self, code, lang):
        ed = self.tabs.currentWidget()
        ext = lang if lang in ('py', 'sh', 'json', 'yaml', 'md', 'sql') else 'py'
        if ed:
            if ed.hasSelectedText():
                ed.replaceSelectedText(code)
            elif not ed.text().strip():
                ed.setText(code)
            else:
                dlg = DiffDialog(ed.text(), code, self)
                res = dlg.exec()
                if res == 1:
                    ed.setText(code)
                elif res == 2:
                    self.create_empty_tab(code, ext)
        else:
            self.create_empty_tab(code, ext)

    def on_ask_ai_selection(self, selected_code, ext):
        if selected_code.startswith("@@COUNCIL@@"):
            raw_c = selected_code.replace("@@COUNCIL@@", "", 1)
            prompt = f"@@COUNCIL@@ Audite cet extrait de code `{ext}` (recherche de vulnérabilités, scénario d'exploitation et patch sécurisé) :\n```{ext}\n{raw_c}\n```\n"
            self.send_to_chat_signal.emit(prompt, True)
        else:
            prompt = f"Corrige, sécurise ou optimise cet extrait de code `{ext}` :\n```{ext}\n{selected_code}\n```\n"
            self.send_to_chat_signal.emit(prompt, True)

    def send_error_to_ai(self):
        ed = self.tabs.currentWidget()
        if not ed or not self.last_error_output: return
        fname = os.path.basename(ed.filepath) if ed.filepath else f"script.{ed.ext}"
        prompt = (
            f"Mon fichier `{fname}` génère l'erreur suivante lors de la vérification/exécution :\n"
            f"```text\n{self.last_error_output}\n```\n\n"
            f"Voici le code source actuel de `{fname}` :\n"
            f"```{ed.ext}\n{ed.text()}\n```\n\n"
            f"Explique brièvement la cause et fournis le code complet corrigé."
        )
        self.send_to_chat_signal.emit(prompt, True)

    def git_status(self):
        res = subprocess.run(["git", "status", "-s", "-b"], cwd=self.current_project_dir, capture_output=True, text=True)
        out = res.stdout or res.stderr or "Aucun dépôt Git détecté."
        self.btn_fix_err.hide()
        self.console_out.setPlainText(f"📊 Git Status ({self.current_project_dir}) :\n{out}")

    def git_diff(self):
        res = subprocess.run(["git", "diff"], cwd=self.current_project_dir, capture_output=True, text=True)
        out = res.stdout or res.stderr or "Aucune modification non indexée."
        self.btn_fix_err.hide()
        self.console_out.setPlainText(f"🔍 Git Diff :\n{out[:8000]}")

    def git_commit_ai(self):
        res = subprocess.run(["git", "diff", "--staged"], cwd=self.current_project_dir, capture_output=True, text=True)
        diff_txt = res.stdout.strip()
        if not diff_txt:
            res2 = subprocess.run(["git", "diff"], cwd=self.current_project_dir, capture_output=True, text=True)
            diff_txt = res2.stdout.strip()
        if not diff_txt:
            self.console_out.setPlainText("ℹ️ Aucun changement Git détecté pour générer un message de commit.")
            return
        prompt = f"Rédige un message de commit Git clair et normé (Conventional Commits en français) pour ces modifications :\n```diff\n{diff_txt[:6000]}\n```\n"
        self.send_to_chat_signal.emit(prompt, True)

    def update_tab_title(self, editor, modified):
        idx = self.tabs.indexOf(editor)
        if idx == -1: return
        base = os.path.basename(editor.filepath) if editor.filepath else f"brouillon.{editor.ext}"
        self.tabs.setTabText(idx, f"{base} *" if modified else base)

    def close_tab(self, index):
        self.tabs.removeTab(index)

    def save_current_tab(self):
        ed = self.tabs.currentWidget()
        if not ed: return
        if not ed.filepath:
            path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder le fichier", self.current_project_dir)
            if not path: return
            ed.filepath = path
            ed.ext = os.path.splitext(path)[1].lstrip('.') or 'py'
            ed.apply_lexer(ed.ext, ed.font())
        with open(ed.filepath, 'w', encoding='utf-8') as f:
            f.write(ed.text())
        ed.setModified(False)
        self.update_tab_title(ed, False)
        self.console_out.setPlainText(f"✅ Fichier sauvegardé : {ed.filepath}")

    def lint_current_tab(self):
        ed = self.tabs.currentWidget()
        if not ed: return
        self.save_current_tab()
        if not ed.filepath: return

        if ed.filepath.endswith('.py'):
            cmd = [sys.executable, "-m", "py_compile", ed.filepath]
        elif ed.filepath.endswith('.sh'):
            cmd = ["bash", "-n", ed.filepath]
        else:
            self.console_out.setPlainText("ℹ️ Vérification syntaxique disponible pour .py et .sh")
            return

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            self.last_error_output = ""
            self.btn_fix_err.hide()
            self.console_out.setPlainText(f"✅ Syntaxe {os.path.basename(ed.filepath)} : Aucune erreur détectée !")
        else:
            self.last_error_output = res.stderr
            self.btn_fix_err.show()
            self.console_out.setPlainText(f"❌ Erreur de syntaxe :\n{res.stderr}")

    def run_current_tab(self):
        ed = self.tabs.currentWidget()
        if not ed: return
        self.save_current_tab()
        if not ed.filepath: return

        if ed.filepath.endswith('.py'):
            cmd = [sys.executable, ed.filepath]
        elif ed.filepath.endswith('.sh'):
            cmd = ["bash", ed.filepath]
        else:
            self.console_out.setPlainText("ℹ️ Exécution directe supportée pour les scripts .py et .sh")
            return

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=os.path.dirname(ed.filepath))
            if res.returncode != 0 and res.stderr:
                self.last_error_output = res.stderr
                self.btn_fix_err.show()
            else:
                self.last_error_output = ""
                self.btn_fix_err.hide()
            out = res.stdout + ("\n" + res.stderr if res.stderr else "")
            self.console_out.setPlainText(out.strip() or "✅ Exécution terminée (aucune sortie).")
        except subprocess.TimeoutExpired:
            self.console_out.setPlainText("⏱️ Délai d'exécution dépassé (15s).")

class ChatInputEdit(QTextEdit):
    send_requested = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.send_requested.emit()
            return
        super().keyPressEvent(event)

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view().pressed.connect(self.handle_item_pressed)
        self.setModel(QStandardItemModel(self))

    def handle_item_pressed(self, index):
        item = self.model().itemFromIndex(index)
        item.setCheckState(Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked)

    def get_checked_items(self):
        return [self.model().item(i).text() for i in range(self.model().rowCount()) if self.model().item(i).checkState() == Qt.CheckState.Checked]

class SettingsDialog(QDialog):
    def __init__(self, options, embed_model, ollama_url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎛️ Paramètres du Moteur IA & Réseau")
        self.setMinimumWidth(440)
        layout = QFormLayout(self)

        url_layout = QHBoxLayout()
        self.edit_url = QLineEdit(ollama_url)
        btn_ping = QPushButton("🔌 Tester")
        btn_ping.clicked.connect(self.test_connection)
        url_layout.addWidget(self.edit_url)
        url_layout.addWidget(btn_ping)
        layout.addRow("URL Serveur Ollama :", url_layout)

        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(0.0, 1.5)
        self.spin_temp.setSingleStep(0.05)
        self.spin_temp.setValue(options.get("temperature", 0.7))
        layout.addRow("Température (0.1=Code, 0.7=Créatif) :", self.spin_temp)

        self.spin_ctx = QSpinBox()
        self.spin_ctx.setRange(2048, 32768)
        self.spin_ctx.setSingleStep(2048)
        self.spin_ctx.setValue(options.get("num_ctx", 8192))
        layout.addRow("Fenêtre de contexte (Tokens) :", self.spin_ctx)

        self.spin_pred = QSpinBox()
        self.spin_pred.setRange(512, 8192)
        self.spin_pred.setSingleStep(512)
        self.spin_pred.setValue(options.get("num_predict", 2048))
        layout.addRow("Longueur max de réponse :", self.spin_pred)

        self.combo_embed = QComboBox()
        self.combo_embed.addItems(["nomic-embed-text", "bge-m3"])
        self.combo_embed.setCurrentText(embed_model)
        layout.addRow("Modèle d'Embeddings RAG :", self.combo_embed)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def test_connection(self):
        url = self.edit_url.text().strip().rstrip('/')
        try:
            r = requests.get(f"{url}/api/tags", timeout=3)
            r.raise_for_status()
            models = [m.get("name") for m in r.json().get("models", [])]
            QMessageBox.information(self, "Connexion réussie", f"✅ Serveur Ollama joignable !\nModèles détectés ({len(models)}) :\n" + ", ".join(models[:8]))
        except Exception as e:
            QMessageBox.critical(self, "Échec de connexion", f"❌ Impossible de joindre {url} :\n{e}")

class IndexerWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, docs_dir, db_dir, collection_name, embed_model="nomic-embed-text", ollama_url="http://127.0.0.1:11434"):
        super().__init__()
        self.docs_dir, self.db_dir, self.collection_name = docs_dir, db_dir, collection_name
        self.embed_model, self.ollama_url = embed_model, ollama_url.rstrip('/')

    def run(self):
        try:
            from langchain_community.document_loaders import PyPDFDirectoryLoader
            from langchain_core.documents import Document
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            from langchain_community.embeddings import OllamaEmbeddings
            from langchain_community.vectorstores import Chroma

            self.progress_signal.emit("Lecture des PDF et fichiers texte/code...")
            docs = PyPDFDirectoryLoader(self.docs_dir).load()

            valid_exts = ('.txt', '.md', '.py', '.sh', '.conf', '.log', '.csv', '.json')
            for root, _, files in os.walk(self.docs_dir):
                for file in files:
                    if file.lower().endswith(valid_exts):
                        full_path = os.path.join(root, file)
                        try:
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                docs.append(Document(page_content=f.read(), metadata={"source": full_path, "page": 1}))
                        except Exception:
                            pass

            if not docs:
                self.error_signal.emit(f"Aucun document supporté trouvé dans {self.docs_dir}")
                return

            self.progress_signal.emit("Découpage du texte...")
            chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(docs)

            self.progress_signal.emit(f"Vectorisation de {len(chunks)} segments ({self.embed_model})...")
            embeddings = OllamaEmbeddings(model=self.embed_model, base_url=self.ollama_url)

            if os.path.exists(self.db_dir): shutil.rmtree(self.db_dir)
            Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=self.db_dir, collection_name=self.collection_name)

            bm25_corpus = [{"page_content": c.page_content, "metadata": c.metadata} for c in chunks]
            with open(os.path.join(self.db_dir, "bm25_corpus.json"), 'w', encoding='utf-8') as f:
                json.dump(bm25_corpus, f, ensure_ascii=False)

            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))

class LibraryManagerDialog(QDialog):
    def __init__(self, embed_model="nomic-embed-text", ollama_url="http://127.0.0.1:11434", parent=None):
        super().__init__(parent)
        self.embed_model, self.ollama_url = embed_model, ollama_url
        self.setWindowTitle("Bibliothèques RAG Hybride (Vecteurs + BM25)")
        self.setMinimumWidth(520)
        self.layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("➕ Nouvelle")
        btn_add.clicked.connect(self.add_library)
        btn_layout.addWidget(btn_add)
        btn_index = QPushButton("🔄 Indexer (Vecteurs + BM25)")
        btn_index.clicked.connect(self.index_library)
        btn_layout.addWidget(btn_index)
        btn_del = QPushButton("🗑️ Supprimer")
        btn_del.setStyleSheet("background-color: #f38ba8; color: #11111b; border: none;")
        btn_del.clicked.connect(self.delete_library)
        btn_layout.addWidget(btn_del)

        self.layout.addLayout(btn_layout)
        self.load_libraries()

    def load_libraries(self):
        self.list_widget.clear()
        with open(LIBRARIES_FILE, 'r', encoding='utf-8') as f:
            self.libs = json.load(f)
        for name, paths in self.libs.items():
            self.list_widget.addItem(f"{name} -> {paths['docs_dir']}")

    def add_library(self):
        name, ok = QInputDialog.getText(self, "Nouvelle Bibliothèque", "Nom :")
        if ok and name:
            folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier de documents")
            if folder:
                self.libs[name] = {"docs_dir": folder, "db_dir": os.path.join(APP_DIR, "chroma_dbs", name.replace(" ", "_").lower())}
                with open(LIBRARIES_FILE, 'w', encoding='utf-8') as f: json.dump(self.libs, f, indent=4, ensure_ascii=False)
                self.load_libraries()

    def delete_library(self):
        item = self.list_widget.currentItem()
        if not item: return
        name = item.text().split(" -> ")[0]
        if os.path.exists(self.libs[name]["db_dir"]): shutil.rmtree(self.libs[name]["db_dir"])
        del self.libs[name]
        with open(LIBRARIES_FILE, 'w', encoding='utf-8') as f: json.dump(self.libs, f, indent=4, ensure_ascii=False)
        self.load_libraries()

    def index_library(self):
        item = self.list_widget.currentItem()
        if not item: return
        name = item.text().split(" -> ")[0]
        lib = self.libs[name]
        self.progress = QProgressDialog("Préparation...", "Annuler", 0, 0, self)
        self.progress.setWindowTitle("Indexation Hybride")
        self.progress.show()

        self.indexer = IndexerWorker(lib["docs_dir"], lib["db_dir"], name.replace(" ", "_").lower(), self.embed_model, self.ollama_url)
        self.indexer.progress_signal.connect(self.progress.setLabelText)
        self.indexer.finished_signal.connect(lambda: [self.progress.accept(), QMessageBox.information(self, "Succès", "Indexation Vectorielle + BM25 terminée !")])
        self.indexer.error_signal.connect(lambda err: [self.progress.accept(), QMessageBox.critical(self, "Erreur", err)])
        self.indexer.start()

class Worker(QThread):
    chunk_received = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    rag_info_signal = pyqtSignal(str)
    rag_sources_signal = pyqtSignal(list)
    speed_signal = pyqtSignal(float)

    def __init__(self, model, messages, options, rag_libs=None, embed_model="nomic-embed-text", ollama_url="http://127.0.0.1:11434"):
        super().__init__()
        self.model, self.messages, self.options, self.rag_libs = model, messages, options, rag_libs or []
        self.embed_model, self.ollama_url = embed_model, ollama_url.rstrip('/')
        self._is_cancelled = False

    def stop(self):
        self._is_cancelled = True

    def run(self):
        self._is_cancelled = False
        if self.rag_libs:
            try:
                from langchain_community.embeddings import OllamaEmbeddings
                from langchain_community.vectorstores import Chroma
                from rank_bm25 import BM25Okapi

                embeddings = OllamaEmbeddings(model=self.embed_model, base_url=self.ollama_url)
                user_msg = self.messages[-1]["content"]
                combined_chunks = []
                seen_texts = set()
                k_per_lib = max(1, 3 // len(self.rag_libs)) if len(self.rag_libs) > 0 else 2

                for lib in self.rag_libs:
                    if self._is_cancelled: return
                    db_dir = lib["db_dir"]
                    if os.path.exists(db_dir):
                        db = Chroma(persist_directory=db_dir, embedding_function=embeddings, collection_name=os.path.basename(db_dir))
                        for d in db.similarity_search(user_msg, k=k_per_lib):
                            if d.page_content not in seen_texts:
                                seen_texts.add(d.page_content)
                                combined_chunks.append({"page_content": d.page_content, "metadata": d.metadata})

                        bm25_file = os.path.join(db_dir, "bm25_corpus.json")
                        if os.path.exists(bm25_file):
                            with open(bm25_file, 'r', encoding='utf-8') as f:
                                corpus = json.load(f)
                            if corpus:
                                tokenized_corpus = [re.findall(r'\w+', doc["page_content"].lower()) for doc in corpus]
                                bm25 = BM25Okapi(tokenized_corpus)
                                query_tokens = re.findall(r'\w+', user_msg.lower())
                                top_bm25 = bm25.get_top_n(query_tokens, corpus, n=k_per_lib)
                                for d in top_bm25:
                                    if d["page_content"] not in seen_texts:
                                        seen_texts.add(d["page_content"])
                                        combined_chunks.append(d)

                if combined_chunks and not self._is_cancelled:
                    context = ""
                    sources_labels = []
                    rich_sources = []
                    for d in combined_chunks:
                        meta = d.get("metadata", {})
                        full_path = meta.get("source", "Inconnu")
                        page = meta.get("page", "?")
                        label = f"{os.path.basename(full_path)} (p.{page})"
                        context += f"--- Source: {label} ---\n{d['page_content']}\n\n"
                        sources_labels.append(label)
                        rich_sources.append({
                            "label": label,
                            "path": full_path,
                            "page": page,
                            "snippet": d["page_content"]
                        })

                    self.rag_info_signal.emit(f"📚 RAG Hybride : {', '.join(dict.fromkeys(sources_labels))}")
                    self.rag_sources_signal.emit(rich_sources)
                    self.messages[-1]["content"] = f"Réponds avec le contexte ci-dessous. Cite tes sources.\n\nCONTEXTE:\n{context}\n\nQUESTION:\n{user_msg}"
                else:
                    self.rag_info_signal.emit("⚠️ Aucune information trouvée.")
            except Exception as e:
                self.error_signal.emit(f"Erreur RAG : {str(e)}")
                return

        if self._is_cancelled: return

        recent_msgs = [self.messages[0]] + self.messages[-10:] if len(self.messages) > 11 else self.messages
        payload = {"model": self.model, "messages": recent_msgs, "stream": True, "options": self.options, "keep_alive": "30m"}
        try:
            resp = requests.post(f"{self.ollama_url}/api/chat", json=payload, stream=True)
            resp.raise_for_status()
            for line in resp.iter_lines():
                if self._is_cancelled:
                    resp.close()
                    break
                if line:
                    data = json.loads(line)
                    self.chunk_received.emit(data.get("message", {}).get("content", ""))
                    if data.get("done") and data.get("eval_duration"):
                        tps = data.get("eval_count", 0) / (data.get("eval_duration", 1) / 1e9)
                        self.speed_signal.emit(tps)
            self.finished_signal.emit()
        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(str(e))

class PullModelWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, model_name, ollama_url):
        super().__init__()
        self.model_name = model_name
        self.ollama_url = ollama_url.rstrip('/')

    def run(self):
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/pull",
                json={"name": self.model_name, "stream": True},
                stream=True, timeout=600
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "Téléchargement...")
                    completed = data.get("completed", 0)
                    total = data.get("total", 0)
                    if total > 0:
                        pct = int((completed / total) * 100)
                        self.progress_signal.emit(f"⬇️ {self.model_name} : {status} ({pct}%)")
                    else:
                        self.progress_signal.emit(f"⬇️ {self.model_name} : {status}")
            self.finished_signal.emit(True, f"✅ Le modèle '{self.model_name}' est installé et prêt à l'emploi !")
        except Exception as e:
            self.finished_signal.emit(False, f"❌ Erreur lors du téléchargement de '{self.model_name}' :\n{e}")

class CouncilDialog(QDialog):
    """Sélecteur des modèles Red Team, Blue Team et Synthèse Purple Team."""
    def __init__(self, ollama_url, current_model, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚔️ Configuration du Conseil Multi-Experts Cyber (Red vs Blue)")
        self.setMinimumWidth(520)
        layout = QFormLayout(self)

        installed = []
        try:
            r = requests.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=3)
            if r.status_code == 200:
                installed = [m.get("name") for m in r.json().get("models", []) if m.get("name")]
        except Exception:
            pass

        default_models = [
            "jimscard/whiterabbit-neo",
            "huihui_ai/baronllm-abliterated",
            "hf.co/BugTraceAI/BugTraceAI-CORE-Pro",
            "hf.co/MaziyarPanahi/VulnLLM-R-7B-GGUF:Q4_K_M",
            "hf.co/gabriellarson/Foundation-Sec-8B-Instruct-GGUF:Q4_K_M",
            "hf.co/mradermacher/CyberSecQwen-4B-GGUF:Q4_K_M",
            "hf.co/mradermacher/RedSage-8B-Cyber-GGUF:Q4_K_M",
            "qwen2.5-coder:7b",
            "deepseek-r1:7b",
            "qwen2.5:7b-instruct",
            "mistral:7b-instruct"
        ]
        all_choices = list(dict.fromkeys(installed + default_models))

        self.combo_red = QComboBox()
        self.combo_red.setEditable(True)
        self.combo_red.addItems(all_choices)

        self.combo_blue = QComboBox()
        self.combo_blue.setEditable(True)
        self.combo_blue.addItems(all_choices)

        self.combo_purple = QComboBox()
        self.combo_purple.setEditable(True)
        self.combo_purple.addItems(all_choices)

        def pick_best(candidates, fallback):
            for c in candidates:
                for inst in installed:
                    if c.lower() in inst.lower():
                        return inst
            return installed[0] if installed else fallback

        self.combo_red.setCurrentText(pick_best(["whiterabbit", "baronllm", "bugtrace", "deepseek", "qwen2.5-coder"], current_model))
        self.combo_blue.setCurrentText(pick_best(["foundation-sec", "vulnllm", "cybersecqwen", "qwen2.5-coder"], current_model))
        self.combo_purple.setCurrentText(pick_best(["redsage", "deepseek", "qwen2.5:7b", "mistral"], current_model))

        self.chk_purple = QCheckBox("Inclure la 3e passe de synthèse Purple Team (Matrice CWE / MITRE & Plan d'action)")
        self.chk_purple.setChecked(True)

        info = QLabel(
            "💡 Les experts s'exécutent séquentiellement pour respecter vos 4 Go de VRAM.\n"
            "L'expert Blue Team reçoit automatiquement l'attaque trouvée par la Red Team pour la contrer."
        )
        info.setStyleSheet("color: #a6e3a1; font-size: 12px;")
        layout.addRow(info)
        layout.addRow("🔴 Expert Offensif (Red Team / Pentest) :", self.combo_red)
        layout.addRow("🔵 Expert Défensif (Blue Team / Patch) :", self.combo_blue)
        layout.addRow("🟣 Arbitre & Gouvernance (Purple Team) :", self.combo_purple)
        layout.addRow(self.chk_purple)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)


class CouncilWorker(QThread):
    chunk_received = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    speed_signal = pyqtSignal(float)

    def __init__(self, user_prompt, red_model, blue_model, purple_model, include_purple, options, ollama_url):
        super().__init__()
        self.user_prompt = user_prompt
        self.red_model = red_model
        self.blue_model = blue_model
        self.purple_model = purple_model
        self.include_purple = include_purple
        self.options = dict(options)
        self.options["temperature"] = 0.2
        self.ollama_url = ollama_url.rstrip('/')
        self._is_cancelled = False

    def stop(self):
        self._is_cancelled = True

    def stream_step(self, model, sys_prompt, user_content, header_md):
        self.chunk_received.emit(header_md)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content}
            ],
            "stream": True,
            "options": self.options,
            "keep_alive": "10m"
        }
        collected = []
        resp = requests.post(f"{self.ollama_url}/api/chat", json=payload, stream=True, timeout=300)
        resp.raise_for_status()
        for line in resp.iter_lines():
            if self._is_cancelled:
                resp.close()
                break
            if line:
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    collected.append(token)
                    self.chunk_received.emit(token)
                if data.get("done") and data.get("eval_duration"):
                    tps = data.get("eval_count", 0) / (data.get("eval_duration", 1) / 1e9)
                    self.speed_signal.emit(tps)
        return "".join(collected)

    def run(self):
        try:
            self.status_signal.emit(f"🔴 Passe 1/3 : Audit offensif Red Team ({self.red_model})...")
            red_sys = (
                "Tu es l'Expert Red Team & Pentest Offensif du Conseil Cyber. "
                "Analyse la cible (code, configuration, architecture ou log) fournie par l'utilisateur. "
                "Identifie les vulnérabilités exploitables, détaille le scénario d'attaque concret (vecteur, payload ou commande d'exploitation) et l'impact technique."
            )
            red_header = f"## 🔴 1. Analyse Offensive & Vecteurs d'Attaque (Red Team — `{self.red_model}`)\n\n"
            red_out = self.stream_step(self.red_model, red_sys, self.user_prompt, red_header)
            if self._is_cancelled:
                self.finished_signal.emit()
                return

            self.status_signal.emit(f"🔵 Passe 2/3 : Contre-mesures & Patch Blue Team ({self.blue_model})...")
            blue_sys = (
                "Tu es l'Expert Blue Team, AppSec & SOC du Conseil Cyber. "
                "Tu reçois la demande initiale de l'utilisateur ainsi que l'analyse offensive de la Red Team. "
                "Fournis : 1) Le code source ou la configuration intégralement corrigée et durcie, "
                "2) Les règles de détection ou de filtrage (Wazuh, Suricata, pfSense, nftables) permettant de bloquer et détecter l'attaque."
            )
            blue_input = (
                f"DEMANDE / CIBLE INITIALE :\n{self.user_prompt}\n\n"
                f"ATTAQUE IDENTIFIÉE PAR LA RED TEAM :\n{red_out}\n\n"
                f"Propose maintenant la remédiation complète, le code corrigé et les règles de détection."
            )
            blue_header = f"\n\n---\n\n## 🔵 2. Remédiation, Code Corrigé & Détection SOC (Blue Team — `{self.blue_model}`)\n\n"
            blue_out = self.stream_step(self.blue_model, blue_sys, blue_input, blue_header)
            if self._is_cancelled:
                self.finished_signal.emit()
                return

            if self.include_purple:
                self.status_signal.emit(f"🟣 Passe 3/3 : Synthèse Purple Team & Gouvernance ({self.purple_model})...")
                purple_sys = (
                    "Tu es le Directeur Cybersécurité (Purple Team / RSSI / DPO). "
                    "À partir du rapport Red Team et du correctif Blue Team, dresse un tableau Markdown synthétique contenant : "
                    "Vulnérabilité (CWE / MITRE ATT&CK), Criticité, Risque métier/RGPD et Action prioritaire." + GRAPH_INSTRUCTIONS
                )
                purple_input = (
                    f"CIBLE :\n{self.user_prompt}\n\n"
                    f"RAPPORT RED TEAM :\n{red_out}\n\n"
                    f"RAPPORT BLUE TEAM :\n{blue_out}\n\n"
                    f"Rédige la synthèse exécutive Purple Team sous forme de tableau récapitulatif et plan d'action."
                )
                purple_header = f"\n\n---\n\n## 🟣 3. Synthèse Purple Team & Matrice de Remédiation (`{self.purple_model}`)\n\n"
                self.stream_step(self.purple_model, purple_sys, purple_input, purple_header)

            self.status_signal.emit("✅ Conseil Multi-Experts Cyber terminé.")
            self.finished_signal.emit()
        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(f"Erreur Conseil Cyber : {str(e)}")

class ProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Éditer Profils (JSON)")
        self.setMinimumWidth(550)
        self.setMinimumHeight(420)
        layout = QVBoxLayout(self)
        self.editor = QTextEdit()
        with open(PROFILES_FILE, 'r', encoding='utf-8') as f: self.editor.setPlainText(f.read())
        layout.addWidget(self.editor)
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_profiles)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def save_profiles(self):
        try:
            data = json.loads(self.editor.toPlainText())
            with open(PROFILES_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
            self.accept()
        except Exception as e: QMessageBox.critical(self, "Erreur JSON", str(e))

class AssistantGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MIA - Assistant IA Souverain, Pédagogie & Atelier Code")
        self.setMinimumSize(850, 560)

        # Calibrage strict sur la géométrie disponible de l'écran (empêche le débordement sous Ubuntu/Wayland)
        screen_geom = QApplication.primaryScreen().availableGeometry()
        self.setMaximumSize(screen_geom.width(), screen_geom.height())
        init_w = min(1360, int(screen_geom.width() * 0.92))
        init_h = min(820, int(screen_geom.height() * 0.88))
        self.resize(init_w, init_h)
        self.move(
            screen_geom.x() + (screen_geom.width() - init_w) // 2,
            screen_geom.y() + (screen_geom.height() - init_h) // 2
        )

        self.current_chat_id = None
        self.messages = []
        self.pending_images = []
        self.model_options = {"temperature": 0.5, "top_p": 0.9, "num_ctx": 8192, "num_predict": 2048}
        self.embed_model = "nomic-embed-text"
        self.ollama_url = "http://127.0.0.1:11434"
        self.last_tps = 0.0

        self.init_systray()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(6, 6, 6, 6)
        self.splitter = QSplitter()
        self.splitter.setChildrenCollapsible(True)
        layout.addWidget(self.splitter)

        # --- VOLET 1 : HISTORIQUE ---
        self.left_panel = QWidget()
        self.left_panel.setMinimumWidth(180)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 4, 0)
        btn_new = QPushButton("✨ Nouvelle Conversation")
        btn_new.clicked.connect(self.new_chat)
        left_layout.addWidget(btn_new)

        self.search_history = QLineEdit()
        self.search_history.setPlaceholderText("🔍 Filtrer l'historique...")
        self.search_history.textChanged.connect(self.filter_history_list)
        left_layout.addWidget(self.search_history)

        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.load_chat)
        self.chat_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chat_list.customContextMenuRequested.connect(self.show_chat_context_menu)
        left_layout.addWidget(self.chat_list)

        btn_del = QPushButton("🗑️ Supprimer")
        btn_del.setStyleSheet("background-color: #f38ba8; color: #11111b; border: none;")
        btn_del.clicked.connect(self.delete_chat)
        left_layout.addWidget(btn_del)

        self.btn_export = QPushButton("📤 Exporter / Pédagogie...")
        self.btn_export.setStyleSheet("background-color: #89b4fa; color: #11111b; border: none;")
        export_menu = QMenu(self)
        act_pdf = QAction("📄 Exporter en PDF", self)
        act_pdf.triggered.connect(self.export_pdf)
        act_md = QAction("📝 Exporter en Markdown (.md)", self)
        act_md.triggered.connect(self.export_markdown)
        act_doku = QAction("📚 Exporter en DokuWiki (.txt)", self)
        act_doku.triggered.connect(self.export_dokuwiki)
        export_menu.addSeparator()
        act_slides = QAction("📽️ Exporter en Présentation Slides (.html)", self)
        act_slides.triggered.connect(self.export_slides)
        act_gift = QAction("🎯 Exporter QCM au format Moodle (.gift)", self)
        act_gift.triggered.connect(self.export_moodle_gift)
        export_menu.addAction(act_pdf)
        export_menu.addAction(act_md)
        export_menu.addAction(act_doku)
        export_menu.addAction(act_slides)
        export_menu.addAction(act_gift)
        self.btn_export.setMenu(export_menu)
        left_layout.addWidget(self.btn_export)

        # --- VOLET 2 : CHAT IA ---
        center_panel = QWidget()
        center_panel.setMinimumWidth(380)
        right_layout = QVBoxLayout(center_panel)
        right_layout.setContentsMargins(4, 0, 4, 0)

        # Barre supérieure épurée (zéro débordement horizontal)
        top_bar = QHBoxLayout()
        btn_toggle_hist = QPushButton("☰")
        btn_toggle_hist.setToolTip("Afficher / Masquer l'historique")
        btn_toggle_hist.setFixedWidth(34)
        btn_toggle_hist.clicked.connect(lambda: self.left_panel.setVisible(not self.left_panel.isVisible()))
        top_bar.addWidget(btn_toggle_hist)

        self.combo_profile = QComboBox()
        self.combo_profile.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_profile.setMinimumContentsLength(18)
        self.combo_profile.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.load_profiles()
        self.combo_profile.currentTextChanged.connect(self.on_profile_changed)
        top_bar.addWidget(self.combo_profile, 1)

        self.chk_rag = QCheckBox("📚 RAG")
        top_bar.addWidget(self.chk_rag)

        self.combo_rag = CheckableComboBox()
        self.combo_rag.setMinimumWidth(110)
        self.combo_rag.setMaximumWidth(160)
        self.load_rag_combo()
        top_bar.addWidget(self.combo_rag)

        # Menu regroupé Outils & Configuration
        btn_tools = QPushButton("🛠️ Outils & Config")
        tools_menu = QMenu(self)
        act_pull = QAction("⬇️ Télécharger / Installer le LLM du profil actif", self)
        act_pull.triggered.connect(self.pull_active_profile_model)
        tools_menu.addAction(act_pull)
        tools_menu.addSeparator()
        act_settings = QAction("🎛️ Paramètres Moteur & URL Ollama", self)
        act_settings.triggered.connect(self.open_settings)
        act_profiles = QAction("✏️ Éditer les Profils IA (JSON)", self)
        act_profiles.triggered.connect(self.open_profile_editor)
        act_libs = QAction("⚙️ Gérer les Bibliothèques RAG (Vecteurs + BM25)", self)
        act_libs.triggered.connect(self.open_library_manager)
        tools_menu.addSeparator()
        act_grader = QAction("🎓 Correcteur de Copies / TP par Lot", self)
        act_grader.triggered.connect(self.open_batch_grader)
        tools_menu.addAction(act_settings)
        tools_menu.addAction(act_profiles)
        tools_menu.addAction(act_libs)
        tools_menu.addSeparator()
        tools_menu.addAction(act_grader)
        btn_tools.setMenu(tools_menu)
        top_bar.addWidget(btn_tools)

        self.btn_toggle_ide = QPushButton("💻 Atelier Code")
        self.btn_toggle_ide.setCheckable(True)
        self.btn_toggle_ide.setStyleSheet("QPushButton:checked { background-color: #a6e3a1; color: #11111b; }")
        self.btn_toggle_ide.toggled.connect(self.toggle_code_studio)
        top_bar.addWidget(self.btn_toggle_ide)

        right_layout.addLayout(top_bar)

        self.webview_ready = False
        self.pending_js_call = None
        self.webview = QWebEngineView()
        self.web_page = BridgeWebPage(self.webview)
        self.web_page.code_received.connect(self.on_code_sent_to_ide)
        self.web_page.source_clicked.connect(self.on_source_badge_clicked)
        self.webview.setPage(self.web_page)
        self.webview.loadFinished.connect(self.on_webview_loaded)
        self.webview.setHtml(HTML_TEMPLATE, QUrl.fromLocalFile(APP_DIR + "/"))
        right_layout.addWidget(self.webview, 1)

        mid_bar = QHBoxLayout()
        self.combo_quick = QComboBox()
        self.combo_quick.addItems(QUICK_PROMPTS.keys())
        self.combo_quick.currentTextChanged.connect(self.apply_quick_prompt)
        mid_bar.addWidget(self.combo_quick)

        btn_regen = QPushButton("🔄 Régénérer")
        btn_regen.clicked.connect(self.regenerate_last)
        mid_bar.addWidget(btn_regen)

        btn_latex = QPushButton("∑ Équation LaTeX")
        btn_latex.setToolTip("Ouvrir l'éditeur visuel d'équations mathématiques")
        btn_latex.clicked.connect(self.open_latex_editor)
        mid_bar.addWidget(btn_latex)

        btn_council = QPushButton("⚔️ Conseil Cyber (Red/Blue)")
        btn_council.setToolTip("Confronter un expert offensif (Red Team) et un expert défensif (Blue Team) sur votre prompt ou code")
        btn_council.setStyleSheet("background-color: #cba6f7; color: #11111b; border: none;")
        btn_council.clicked.connect(self.launch_cyber_council)
        mid_bar.addWidget(btn_council)

        self.stream_render_timer = QTimer(self)
        self.stream_render_timer.setSingleShot(True)
        self.stream_render_timer.timeout.connect(lambda: self.refresh_webview(is_generating=True))

        self.lbl_attachments = QLabel("")
        self.lbl_attachments.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        mid_bar.addWidget(self.lbl_attachments, 1)
        right_layout.addLayout(mid_bar)

        input_layout = QHBoxLayout()
        self.input_field = ChatInputEdit()
        self.input_field.setMaximumHeight(80)
        self.input_field.setPlaceholderText("Posez votre question ici... (Ctrl+Entrée pour envoyer)")
        self.input_field.send_requested.connect(self.send_message)
        input_layout.addWidget(self.input_field, 1)

        self.btn_attach = QPushButton("📎 Joindre")
        self.btn_attach.setMinimumHeight(80)
        self.btn_attach.clicked.connect(self.attach_file)
        input_layout.addWidget(self.btn_attach)

        self.btn_send = QPushButton("🚀 Envoyer")
        self.btn_send.setStyleSheet("background-color: #89b4fa; color: #11111b; border: none;")
        self.btn_send.setMinimumHeight(80)
        self.btn_send.setMinimumWidth(95)
        self.btn_send.clicked.connect(self.send_message)
        input_layout.addWidget(self.btn_send)

        self.btn_stop = QPushButton("🛑 Stopper")
        self.btn_stop.setStyleSheet("background-color: #f38ba8; color: #11111b; border: none;")
        self.btn_stop.setMinimumHeight(80)
        self.btn_stop.setMinimumWidth(95)
        self.btn_stop.clicked.connect(self.stop_generation)
        self.btn_stop.hide()
        input_layout.addWidget(self.btn_stop)

        right_layout.addLayout(input_layout)

        # --- VOLET 3 : ATELIER CODE ---
        self.code_studio = CodeStudioWidget(self)
        self.code_studio.send_to_chat_signal.connect(self.on_studio_prompt)
        self.code_studio.hide()

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(center_panel)
        self.splitter.addWidget(self.code_studio)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 1)
        self.splitter.setSizes([220, init_w - 220, 0])

        # --- BARRE D'ÉTAT ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_sys_monitor = QLabel("🖥️ Initialisation...")
        self.status_bar.addWidget(self.lbl_sys_monitor, 1)

        btn_free_vram = QPushButton("🧹 Libérer VRAM")
        btn_free_vram.setStyleSheet("background-color: #fab387; color: #11111b; border: none; padding: 2px 8px; font-size: 11.5px;")
        btn_free_vram.clicked.connect(self.unload_vram_models)
        self.status_bar.addPermanentWidget(btn_free_vram)

        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.update_system_monitor)
        self.monitor_timer.start(3000)
        self.update_system_monitor()

        self.load_history_list()
        self.new_chat()

    def update_system_monitor(self):
        ram = psutil.virtual_memory()
        ram_str = f"RAM : {ram.used / (1024**3):.1f}/{ram.total / (1024**3):.1f} Go ({ram.percent}%)"
        vram_str = "VRAM : N/A"
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=1
            )
            if res.returncode == 0 and res.stdout.strip():
                used, total = res.stdout.strip().split('\n')[0].split(',')
                vram_str = f"VRAM : {int(used)}/{int(total)} Mo"
        except Exception:
            pass
        tps_str = f"⚡ {self.last_tps:.1f} tok/s" if self.last_tps > 0 else "⚡ -- tok/s"
        self.lbl_sys_monitor.setText(f"🖥️ {ram_str}  |  🎮 {vram_str}  |  {tps_str}  |  🌐 {self.ollama_url}")

    def pull_active_profile_model(self):
        with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
            prof = json.load(f).get(self.combo_profile.currentText(), {})
        model_name = prof.get("model", "")
        if not model_name: return
        self.pull_prog = QProgressDialog(f"Connexion à Ollama pour télécharger {model_name}...", None, 0, 0, self)
        self.pull_prog.setWindowTitle("⬇️ Téléchargement du modèle IA")
        self.pull_prog.setMinimumWidth(460)
        self.pull_prog.show()

        self.pull_worker = PullModelWorker(model_name, self.ollama_url)
        self.pull_worker.progress_signal.connect(self.pull_prog.setLabelText)
        self.pull_worker.finished_signal.connect(self.on_pull_finished)
        self.pull_worker.start()

    def on_pull_finished(self, ok, msg):
        self.pull_prog.accept()
        if ok:
            QMessageBox.information(self, "Modèle prêt", msg)
        else:
            QMessageBox.critical(self, "Erreur Ollama Pull", msg)

    def unload_vram_models(self):
        with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
            profile = json.load(f).get(self.combo_profile.currentText(), {})
        model = profile.get("model", "")
        try:
            if model:
                requests.post(f"{self.ollama_url.rstrip('/')}/api/generate", json={"model": model, "keep_alive": 0}, timeout=4)
            self.update_system_monitor()
            QMessageBox.information(self, "VRAM libérée", f"✅ Le modèle '{model}' a été déchargé de la mémoire vidéo.")
        except Exception as e:
            QMessageBox.warning(self, "Avertissement", f"Impossible de décharger le modèle : {e}")

    def on_source_badge_clicked(self, src_data):
        SourceViewerDialog(src_data, self).exec()

    def open_batch_grader(self):
        with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
            profile = json.load(f).get(self.combo_profile.currentText(), {})
        BatchGraderDialog(profile.get("model", "qwen2.5:7b-instruct"), self.ollama_url, self).exec()

    def toggle_code_studio(self, checked):
        total_w = self.width()
        left_w = 200 if self.left_panel.isVisible() else 0
        rem_w = max(600, total_w - left_w)
        if checked:
            self.code_studio.show()
            self.splitter.setSizes([left_w, int(rem_w * 0.46), int(rem_w * 0.54)])
        else:
            self.code_studio.hide()
            self.splitter.setSizes([left_w, rem_w, 0])

    def on_code_sent_to_ide(self, code, lang):
        if not self.btn_toggle_ide.isChecked():
            self.btn_toggle_ide.setChecked(True)
        self.code_studio.receive_code_from_chat(code, lang)

    def on_studio_prompt(self, text, auto_send):
        if text.startswith("@@COUNCIL@@"):
            clean_t = text.replace("@@COUNCIL@@", "", 1).strip()
            self.input_field.setPlainText(clean_t)
            self.launch_cyber_council()
            return
        self.input_field.setPlainText(self.input_field.toPlainText() + text)
        if auto_send:
            self.send_message()
        else:
            self.input_field.setFocus()

    def launch_cyber_council(self):
        user_text = self.input_field.toPlainText().strip()
        if not user_text:
            # Si le champ de saisie est vide mais qu'un code est ouvert dans l'Atelier Code, on propose de l'utiliser
            ed = self.code_studio.tabs.currentWidget() if hasattr(self, 'code_studio') else None
            if ed and ed.text().strip():
                fname = os.path.basename(ed.filepath) if ed.filepath else f"script.{ed.ext}"
                user_text = f"Audite ce fichier `{fname}` :\n```{ed.ext}\n{ed.text()}\n```"
            else:
                QMessageBox.information(
                    self, "Conseil Cyber (Red vs Blue)",
                    "Saisissez d'abord une question, collez un log (Wazuh/Suricata/pfSense) ou ouvrez un script dans l'Atelier Code avant de lancer le Conseil."
                )
                return

        with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
            prof = json.load(f).get(self.combo_profile.currentText(), {})
        curr_model = prof.get("model", "qwen2.5-coder:7b")

        dlg = CouncilDialog(self.ollama_url, curr_model, self)
        if not dlg.exec():
            return

        red_m = dlg.combo_red.currentText().strip()
        blue_m = dlg.combo_blue.currentText().strip()
        purple_m = dlg.combo_purple.currentText().strip()
        inc_purple = dlg.chk_purple.isChecked()

        self.input_field.clear()
        if not self.messages:
            self.messages.append({"role": "system", "content": prof.get("sys", "")})

        self.messages.append({"role": "user", "content": f"⚔️ **[Conseil Cyber Red vs Blue]**\n\n{user_text}"})
        self.messages.append({"role": "assistant", "content": ""})
        self.refresh_webview(is_generating=True)

        self.btn_send.hide()
        self.btn_stop.show()

        self.worker = CouncilWorker(user_text, red_m, blue_m, purple_m, inc_purple, self.model_options, self.ollama_url)
        self.worker.chunk_received.connect(self.on_chunk)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error_signal.connect(self.on_error)
        self.worker.status_signal.connect(self.lbl_attachments.setText)
        self.worker.speed_signal.connect(self.on_speed_measured)
        self.worker.start()

    def init_systray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        tray_menu = QMenu()
        show_act = QAction("Afficher", self)
        show_act.triggered.connect(self.show_window)
        quit_act = QAction("Quitter", self)
        quit_act.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(show_act)
        tray_menu.addAction(quit_act)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(lambda r: self.hide() if self.isVisible() else self.show_window() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray_icon.show()

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("MIA en arrière-plan", "Cliquez sur l'icône pour rouvrir.", QSystemTrayIcon.MessageIcon.Information, 2000)

    def load_profiles(self):
        self.combo_profile.clear()
        with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
            self.profiles_cache = json.load(f)
            self.combo_profile.addItems(self.profiles_cache.keys())

    def on_profile_changed(self, profile_name):
        if not profile_name or not hasattr(self, 'profiles_cache'): return
        prof = self.profiles_cache.get(profile_name, {})
        if "temperature" in prof:
            self.model_options["temperature"] = prof["temperature"]
        if "num_ctx" in prof:
            self.model_options["num_ctx"] = prof["num_ctx"]

    def open_profile_editor(self):
        if ProfileDialog(self).exec():
            self.load_profiles()

    def open_settings(self):
        dlg = SettingsDialog(self.model_options, self.embed_model, self.ollama_url, self)
        if dlg.exec():
            self.ollama_url = dlg.edit_url.text().strip().rstrip('/')
            self.model_options["temperature"] = dlg.spin_temp.value()
            self.model_options["num_ctx"] = dlg.spin_ctx.value()
            self.model_options["num_predict"] = dlg.spin_pred.value()
            self.embed_model = dlg.combo_embed.currentText()
            self.update_system_monitor()

    def apply_quick_prompt(self, key):
        template = QUICK_PROMPTS.get(key, "")
        if template:
            current = self.input_field.toPlainText()
            self.input_field.setPlainText(template + current)
            self.combo_quick.setCurrentIndex(0)
            self.input_field.setFocus()

    def load_rag_combo(self):
        self.combo_rag.clear()
        with open(LIBRARIES_FILE, 'r', encoding='utf-8') as f:
            for lib in json.load(f).keys():
                item = QStandardItem(lib)
                item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
                self.combo_rag.model().appendRow(item)

    def open_library_manager(self):
        LibraryManagerDialog(self.embed_model, self.ollama_url, self).exec()
        self.load_rag_combo()

    def attach_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Joindre un fichier", "",
            "Tous supportés (*.py *.sh *.txt *.md *.conf *.log *.csv *.json *.png *.jpg *.jpeg)"
        )
        if not path: return
        if path.lower().endswith(('.png', '.jpg', '.jpeg')):
            with open(path, "rb") as f: self.pending_images.append(base64.b64encode(f.read()).decode('utf-8'))
            self.lbl_attachments.setText(f"📸 {len(self.pending_images)} image(s)")
        else:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                self.input_field.setPlainText(self.input_field.toPlainText() + f"\n\nContenu de `{os.path.basename(path)}`:\n```\n{f.read()}\n```\n")

    def load_history_list(self):
        self.chat_list.clear()
        for f in sorted(os.listdir(CONV_DIR), reverse=True):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(CONV_DIR, f), 'r', encoding='utf-8') as file:
                        self.chat_list.addItem(f"{f.replace('.json', '')} | {json.load(file).get('title', 'Sans titre')}")
                except Exception:
                    pass
        self.filter_history_list(self.search_history.text())

    def filter_history_list(self, query):
        q = query.strip().lower()
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            item.setHidden(q not in item.text().lower())

    def show_chat_context_menu(self, pos):
        item = self.chat_list.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        rename_act = QAction("✏️ Renommer", self)
        del_act = QAction("🗑️ Supprimer", self)
        menu.addAction(rename_act)
        menu.addAction(del_act)
        action = menu.exec(self.chat_list.mapToGlobal(pos))
        if action == rename_act:
            chat_id, old_title = item.text().split(" | ", 1)
            new_title, ok = QInputDialog.getText(self, "Renommer", "Nouveau titre :", text=old_title)
            if ok and new_title.strip():
                filepath = os.path.join(CONV_DIR, f"{chat_id}.json")
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
                    data["title"] = new_title.strip()
                    with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False)
                    self.load_history_list()
        elif action == del_act:
            self.chat_list.setCurrentItem(item)
            self.delete_chat()

    def new_chat(self):
        self.current_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.messages, self.pending_images = [], []
        self.lbl_attachments.setText("")
        self.refresh_webview(is_generating=False)

    def load_chat(self, item):
        self.current_chat_id = item.text().split(" | ")[0]
        with open(os.path.join(CONV_DIR, f"{self.current_chat_id}.json"), 'r', encoding='utf-8') as f:
            self.messages = json.load(f).get("messages", [])
        self.refresh_webview(is_generating=False)

    def delete_chat(self):
        item = self.chat_list.currentItem()
        if item:
            os.remove(os.path.join(CONV_DIR, f"{item.text().split(' | ')[0]}.json"))
            self.load_history_list()
            self.new_chat()

    def export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PDF", "", "PDF (*.pdf)")
        if path:
            from PyQt6.QtGui import QPageLayout, QPageSize
            from PyQt6.QtCore import QMarginsF
            layout = QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                QMarginsF(8, 8, 8, 8),
                QPageLayout.Unit.Millimeter
            )
            self.webview.page().printToPdf(path, layout)

    def export_markdown(self):
        if not self.messages: return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter Markdown", "", "Markdown (*.md)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                for m in self.messages:
                    if m['role'] != 'system':
                        role_label = "Vous" if m['role'] == 'user' else "MIA"
                        f.write(f"## {role_label}\n\n{m['content']}\n\n---\n\n")

    def export_dokuwiki(self):
        if not self.messages: return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter DokuWiki", "", "Texte DokuWiki (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                for m in self.messages:
                    if m['role'] != 'system':
                        role_label = "Question" if m['role'] == 'user' else "Réponse MIA"
                        doku_body = convert_markdown_to_dokuwiki(m['content'])
                        f.write(f"===== {role_label} =====\n\n{doku_body}\n\n----\n\n")

    def export_slides(self):
        if not self.messages: return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter Présentation Slides HTML", "cours_slides.html", "HTML (*.html)")
        if path:
            html = generate_slides_html(self.messages)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def export_moodle_gift(self):
        if not self.messages: return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter QCM Moodle GIFT", "qcm_moodle.gift", "Moodle GIFT (*.gift *.txt)")
        if path:
            gift_txt = extract_moodle_gift(self.messages)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(gift_txt)
            QMessageBox.information(self, "Export Moodle GIFT", f"✅ Fichier GIFT enregistré :\n{path}")

    def save_current_chat(self):
        filepath = os.path.join(CONV_DIR, f"{self.current_chat_id}.json")
        existing_title = None
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_title = json.load(f).get("title")
            except Exception:
                pass
        if not existing_title or existing_title == "Nouveau":
            existing_title = self.messages[1]['content'][:35].replace('\n', ' ') + "..." if len(self.messages) > 1 else "Nouveau"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"title": existing_title, "messages": self.messages}, f, ensure_ascii=False)
        self.load_history_list()

    def refresh_webview(self, is_generating=False):
        messages_html = []
        for i, msg in enumerate(self.messages):
            is_last_gen = (is_generating and i == len(self.messages) - 1)
            md = format_message_html(msg['content'], is_generating=is_last_gen, rag_sources=msg.get("rag_sources"))

            if msg['role'] == 'user':
                messages_html.append(f'<div class="msg-row user"><div class="msg-bubble user"><div class="markdown-body">{md}</div></div></div>')
            elif msg['role'] == 'assistant':
                raw_encoded = urllib.parse.quote(msg['content'])
                btn = f'<button class="copy-btn" data-raw="{raw_encoded}" onclick="copyContent(this)" title="Copier toute la réponse">📋</button>'
                messages_html.append(f'<div class="msg-row assistant"><div class="msg-bubble assistant">{btn}<div class="markdown-body">{md}</div></div></div>')

        js_code = f"if (typeof window.updateChat === 'function') {{ window.updateChat({json.dumps(messages_html)}, {'true' if is_generating else 'false'}); }}"
        if getattr(self, 'webview_ready', False):
            self.webview.page().runJavaScript(js_code)
        else:
            self.pending_js_call = js_code

    def on_webview_loaded(self, ok):
        self.webview_ready = True
        if getattr(self, 'pending_js_call', None):
            self.webview.page().runJavaScript(self.pending_js_call)
            self.pending_js_call = None

    def stop_generation(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.messages[-1]["content"] += "\n\n*(Génération interrompue)*"
            self.refresh_webview(is_generating=False)
            self.on_finished()

    def regenerate_last(self):
        if hasattr(self, 'worker') and self.worker.isRunning(): return
        if len(self.messages) >= 2 and self.messages[-1]['role'] == 'assistant':
            self.messages.pop()
            self.launch_worker()

    def send_message(self):
        user_text = self.input_field.toPlainText().strip()
        if not user_text and not self.pending_images: return

        self.input_field.clear()
        self.lbl_attachments.setText("")

        with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
            profile = json.load(f)[self.combo_profile.currentText()]

        if not self.messages:
            self.messages.append({"role": "system", "content": profile["sys"]})
        else:
            self.messages[0] = {"role": "system", "content": profile["sys"]}

        user_msg = {"role": "user", "content": user_text}
        if self.pending_images: user_msg["images"] = self.pending_images

        self.messages.append(user_msg)
        self.pending_images = []
        self.launch_worker()

    def launch_worker(self):
        self.btn_send.hide()
        self.btn_stop.show()

        with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
            profile = json.load(f)[self.combo_profile.currentText()]

        self.messages.append({"role": "assistant", "content": ""})
        self.refresh_webview(is_generating=True)

        selected_libs = []
        if self.chk_rag.isChecked():
            with open(LIBRARIES_FILE, 'r', encoding='utf-8') as f:
                all_libs = json.load(f)
                selected_libs = [all_libs[n] for n in self.combo_rag.get_checked_items() if n in all_libs]

        self.worker = Worker(profile["model"], self.messages[:-1], self.model_options, selected_libs, self.embed_model, self.ollama_url)
        self.worker.chunk_received.connect(self.on_chunk)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error_signal.connect(self.on_error)
        self.worker.rag_info_signal.connect(self.lbl_attachments.setText)
        self.worker.rag_sources_signal.connect(self.on_rag_sources)
        self.worker.speed_signal.connect(self.on_speed_measured)
        self.worker.start()

    def on_rag_sources(self, sources_list):
        if self.messages and self.messages[-1]['role'] == 'assistant':
            self.messages[-1]['rag_sources'] = sources_list

    def on_speed_measured(self, tps):
        self.last_tps = tps
        self.update_system_monitor()

    def open_latex_editor(self):
        dlg = LatexEditorDialog(self)
        res = dlg.exec()
        tex = dlg.input_tex.toPlainText().strip()
        if res == 1 and tex:
            self.input_field.insertPlainText(f"\n$$\n{tex}\n$$\n")
        elif res == 2 and tex:
            self.input_field.insertPlainText(f" ${tex}$ ")

    def on_chunk(self, chunk):
        self.messages[-1]["content"] += chunk
        if not self.stream_render_timer.isActive():
            self.stream_render_timer.start(120)

    def on_finished(self):
        if hasattr(self, 'stream_render_timer'):
            self.stream_render_timer.stop()
        self.btn_stop.hide()
        self.btn_send.show()
        self.btn_send.setEnabled(True)
        self.refresh_webview(is_generating=False)
        self.save_current_chat()

    def on_error(self, err):
        self.messages[-1]["content"] += f"\n**[Erreur: {err}]**"
        self.refresh_webview(is_generating=False)
        self.on_finished()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_QSS)
    app.setQuitOnLastWindowClosed(False)
    gui = AssistantGUI()
    gui.show()
    sys.exit(app.exec())
