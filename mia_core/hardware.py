import json
import os
import re
import subprocess
import psutil
import requests

APP_DIR = os.path.expanduser("~/.local/share/mia-app")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
PROFILES_FILE = os.path.join(APP_DIR, "profiles.json")
LIBRARIES_FILE = os.path.join(APP_DIR, "libraries.json")


def detect_hardware():
    """Détecte les caractéristiques CPU, RAM et GPU NVIDIA de la machine locale."""
    cpu_phys = psutil.cpu_count(logical=False) or 4
    cpu_log = psutil.cpu_count(logical=True) or cpu_phys
    vm = psutil.virtual_memory()
    ram_total_gb = round(vm.total / (1024 ** 3), 1)
    ram_avail_gb = round(vm.available / (1024 ** 3), 1)

    gpu_name = "CPU / iGPU uniquement"
    vram_total_mb = 0
    vram_used_mb = 0
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().splitlines()[0].split(",")]
            if len(parts) >= 3:
                gpu_name = parts[0]
                vram_used_mb = int(float(parts[1]))
                vram_total_mb = int(float(parts[2]))
    except Exception:
        pass

    if vram_total_mb <= 4600:
        tier = "eco_4gb"
    elif vram_total_mb <= 10500:
        tier = "standard_8gb"
    else:
        tier = "max_12gb"

    return {
        "cpu_physical": cpu_phys,
        "cpu_logical": cpu_log,
        "ram_total_gb": ram_total_gb,
        "ram_avail_gb": ram_avail_gb,
        "gpu_name": gpu_name,
        "vram_total_mb": vram_total_mb,
        "vram_used_mb": vram_used_mb,
        "vram_free_mb": max(0, vram_total_mb - vram_used_mb),
        "recommended_tier": tier,
    }


TIER_LABELS = {
    "eco_4gb": "⚡ Éco 4Go",
    "standard_8gb": "⚖️ Standard",
    "max_12gb": "🚀 Max",
}


def get_tier_defaults(tier, hw=None):
    """Retourne les paramètres Ollama recommandés pour un palier matériel donné."""
    hw = hw or detect_hardware()
    phys = hw["cpu_physical"]
    if tier == "eco_4gb":
        return {
            "num_ctx": 4096,
            "num_batch": 256,
            "num_thread": phys,
            "num_gpu": -1,
            "auto_unload_vram": True,
            "rag_embed_cpu": True,
            "keep_alive": "10m",
        }
    if tier == "standard_8gb":
        return {
            "num_ctx": 8192,
            "num_batch": 512,
            "num_thread": phys,
            "num_gpu": -1,
            "auto_unload_vram": False,
            "rag_embed_cpu": False,
            "keep_alive": "20m",
        }
    return {
        "num_ctx": 12288,
        "num_batch": 512,
        "num_thread": phys,
        "num_gpu": -1,
        "auto_unload_vram": False,
        "rag_embed_cpu": False,
        "keep_alive": "30m",
    }


def load_settings(hw=None):
    """Charge settings.json ou génère des valeurs calibrées pour le matériel détecté."""
    hw = hw or detect_hardware()
    rec_tier = hw["recommended_tier"]
    tier_cfg = get_tier_defaults(rec_tier, hw)

    defaults = {
        "ollama_url": "http://127.0.0.1:11434",
        "embed_model": "nomic-embed-text",
        "hardware_tier": rec_tier,
        "temperature": 0.5,
        "top_p": 0.9,
        "num_ctx": tier_cfg["num_ctx"],
        "num_predict": 2048,
        "num_thread": tier_cfg["num_thread"],
        "num_batch": tier_cfg["num_batch"],
        "num_gpu": tier_cfg["num_gpu"],
        "auto_unload_vram": tier_cfg["auto_unload_vram"],
        "rag_embed_cpu": tier_cfg["rag_embed_cpu"],
        "quant_4gb_hf": False,
        "quant_4gb_target": "IQ4_XS",
        "keep_alive": tier_cfg["keep_alive"],
    }

    os.makedirs(APP_DIR, exist_ok=True)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                defaults.update(saved)
        except Exception:
            pass
    else:
        save_settings(defaults)
    return defaults


def save_settings(settings):
    """Enregistre settings.json de manière persistante."""
    os.makedirs(APP_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


def build_ollama_options(base_options, settings):
    """Construit le dictionnaire options transmis à Ollama en appliquant les réglages matériels."""
    opts = {
        "temperature": float(base_options.get("temperature", settings.get("temperature", 0.5))),
        "top_p": float(base_options.get("top_p", settings.get("top_p", 0.9))),
        "num_ctx": int(base_options.get("num_ctx", settings.get("num_ctx", 4096))),
        "num_predict": int(base_options.get("num_predict", settings.get("num_predict", 2048))),
        "num_thread": int(settings.get("num_thread", 6)),
        "num_batch": int(settings.get("num_batch", 256)),
    }
    num_gpu = int(settings.get("num_gpu", -1))
    if num_gpu >= 0:
        opts["num_gpu"] = num_gpu
    return opts


def resolve_model_name(model_name, settings):
    """Si la quantification 4 Go HF est activée, adapte :Q4_K_M vers :IQ4_XS ou :Q3_K_M pour les dépôts hf.co."""
    if not model_name:
        return model_name
    if settings.get("quant_4gb_hf") and model_name.startswith("hf.co/") and ":Q4_K_M" in model_name:
        target = settings.get("quant_4gb_target", "IQ4_XS")
        return model_name.replace(":Q4_K_M", f":{target}")
    return model_name


def get_keep_alive_for_model(model_name, settings, default=None):
    """Adapte keep_alive selon le modèle (ex. 2m pour les modèles Vision lourds)."""
    m = (model_name or "").lower()
    if any(v in m for v in ("minicpm-v", "llava", "vision", "bakllava")):
        return "2m"
    if default is not None:
        return default
    return settings.get("keep_alive", "10m")


def get_loaded_ollama_models(ollama_url):
    """Interroge GET /api/ps pour lister les modèles actuellement chargés en VRAM/RAM."""
    url = ollama_url.rstrip("/")
    try:
        r = requests.get(f"{url}/api/ps", timeout=3)
        r.raise_for_status()
        out = []
        for m in r.json().get("models", []):
            name = m.get("name") or m.get("model") or ""
            size_mb = round(m.get("size", 0) / (1024 ** 2))
            vram_mb = round(m.get("size_vram", 0) / (1024 ** 2))
            if name:
                out.append({"name": name, "size_mb": size_mb, "vram_mb": vram_mb})
        return out
    except Exception:
        return []


def unload_ollama_model(ollama_url, model_name):
    """Décharge un modèle précis de la VRAM/RAM via keep_alive: 0."""
    if not model_name:
        return False
    url = ollama_url.rstrip("/")
    try:
        requests.post(
            f"{url}/api/generate",
            json={"model": model_name, "keep_alive": 0},
            timeout=5
        )
        return True
    except Exception:
        return False


def unload_all_ollama_models(ollama_url, fallback_model=None):
    """Décharge tous les modèles actuellement actifs dans Ollama (/api/ps)."""
    loaded = get_loaded_ollama_models(ollama_url)
    unloaded = []
    for item in loaded:
        if unload_ollama_model(ollama_url, item["name"]):
            unloaded.append(item["name"])
    if not unloaded and fallback_model:
        if unload_ollama_model(ollama_url, fallback_model):
            unloaded.append(fallback_model)
    return unloaded


def list_installed_ollama_models(ollama_url, vram_total_mb=4096):
    """Liste les modèles installés (/api/tags) avec taille disque et badge de compatibilité VRAM."""
    url = ollama_url.rstrip("/")
    loaded_names = {m["name"]: m for m in get_loaded_ollama_models(url)}
    r = requests.get(f"{url}/api/tags", timeout=4)
    r.raise_for_status()
    vram_gb = max(1.0, vram_total_mb / 1024.0) if vram_total_mb > 0 else 0.0

    models = []
    for m in r.json().get("models", []):
        name = m.get("name", "")
        size_bytes = m.get("size", 0)
        size_gb = size_bytes / (1024 ** 3)
        details = m.get("details", {}) or {}
        param_size = details.get("parameter_size", "?")
        quant = details.get("quantization_level", "?")

        if vram_gb <= 0:
            compat = "🖥️ CPU"
        elif size_gb <= (vram_gb * 0.85):
            compat = "🟢 100 % VRAM"
        elif size_gb <= (vram_gb * 1.45):
            compat = "🟡 Hybride GPU+CPU"
        else:
            compat = "🔴 Lourd (majorité CPU)"

        in_mem = loaded_names.get(name)
        models.append({
            "name": name,
            "size_gb": round(size_gb, 2),
            "param_size": param_size,
            "quant": quant,
            "compat": compat,
            "loaded": bool(in_mem),
            "vram_mb": in_mem["vram_mb"] if in_mem else 0,
        })
    models.sort(key=lambda x: x["size_gb"], reverse=True)
    return models


def delete_ollama_model(ollama_url, model_name):
    """Supprime un modèle du stockage local d'Ollama via DELETE /api/delete."""
    url = ollama_url.rstrip("/")
    r = requests.delete(f"{url}/api/delete", json={"name": model_name}, timeout=15)
    r.raise_for_status()
    return True


def check_ollama_service_optimizations():
    """Vérifie si les optimisations systemd Ollama (Flash Attention / KV-Cache) sont présentes."""
    dropin = "/etc/systemd/system/ollama.service.d/mia-opt.conf"
    return os.path.exists(dropin)
