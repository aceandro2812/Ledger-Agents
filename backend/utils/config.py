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


def get_db_setting(key: str) -> Optional[str]:
    """Query a setting directly from the SQLite database."""
    import sqlite3
    db_path = "forensic_audit.db"
    if getattr(sys, 'frozen', False):
        db_path = os.path.join(os.path.dirname(sys.executable), db_path)
    
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = c.fetchone()
        conn.close()
        if row:
            return row[0]
    except Exception:
        pass
    return None


def set_db_setting(key: str, value: str) -> None:
    """Insert or update a setting directly in the SQLite database."""
    import sqlite3
    db_path = "forensic_audit.db"
    if getattr(sys, 'frozen', False):
        db_path = os.path.join(os.path.dirname(sys.executable), db_path)
        
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Warning] Failed to write db setting {key}: {e}")


def read_config() -> dict:
    """Read configuration from config.json and merge with database settings."""
    path = get_config_path()
    cfg = {}
    
    # 1. Read from config.json if it exists
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
            
    # 2. Merge database settings (database values override config file)
    db_api_key = get_db_setting("llm_api_key")
    db_model = get_db_setting("llm_model")
    db_base_url = get_db_setting("llm_base_url")
    
    if db_api_key is not None:
        cfg["llm_api_key"] = db_api_key
    if db_model is not None:
        cfg["llm_model"] = db_model
    if db_base_url is not None:
        cfg["llm_base_url"] = db_base_url
        
    return cfg


def write_config(data: dict) -> None:
    """Write configuration dict to config.json and SQLite database."""
    # Write to database settings
    if "llm_api_key" in data:
        set_db_setting("llm_api_key", data["llm_api_key"])
    if "llm_model" in data:
        set_db_setting("llm_model", data["llm_model"])
    if "llm_base_url" in data:
        set_db_setting("llm_base_url", data["llm_base_url"])

    path = get_config_path()
    existing = read_config()
    existing.update(data)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    except Exception as e:
        print(f"[Warning] Failed to write config file: {e}")



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
