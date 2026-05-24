import os
import sys
import json
from typing import Optional

# ---------------------------------------------------------------------------
# Config file path resolution
# In packaged mode (PyInstaller frozen EXE), config.json sits next to the EXE.
# In dev mode, it sits next to the backend/ directory (project root).
# ---------------------------------------------------------------------------

def get_config_path() -> str:
    if getattr(sys, 'frozen', False):
        # Running as a packaged EXE — store config next to the executable
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running in dev mode — store config at the project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "forensic_audit_config.json")


def read_config() -> dict:
    """Read configuration from config.json. Returns empty dict if not found."""
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def write_config(data: dict) -> None:
    """Write configuration dict to config.json."""
    path = get_config_path()
    # Merge with existing config to avoid overwriting unrelated keys
    existing = read_config()
    existing.update(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def is_llm_configured() -> bool:
    """Check if a valid API key exists in config file or env."""
    cfg = read_config()
    if cfg.get("llm_api_key"):
        return True
    
    env_key = os.getenv("LLM_API_KEY")
    if env_key and "REPLACE_WITH_YOUR_KEY" not in env_key and "your-openrouter-key" not in env_key:
        return True
    return False


def get_llm_settings() -> dict:
    """
    Return resolved LLM settings merging config.json and env vars.
    Config file settings take priority over environment variables.
    """
    cfg = read_config()
    
    # Prioritize config.json, fallback to env vars
    api_key = cfg.get("llm_api_key")
    if not api_key:
        env_key = os.getenv("LLM_API_KEY", "")
        if "REPLACE_WITH_YOUR_KEY" not in env_key and "your-openrouter-key" not in env_key:
            api_key = env_key

    model = cfg.get("llm_model") or os.getenv("LLM_MODEL") or "openrouter/google/gemini-2.5-flash:free"
    base_url = cfg.get("llm_base_url") or os.getenv("LLM_BASE_URL") or ""
    
    return {
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
    }
