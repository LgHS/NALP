import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Pas de valeur requise ici: des scripts comme generate_key.py n'ont besoin
    # que de API_KEY_PEPPER. main.py valide bridge_host/bridge_token au demarrage.
    bridge_host: str = os.environ.get("BRIDGE_HOST", "")
    bridge_port: int = int(os.environ.get("BRIDGE_PORT", "8080"))
    bridge_token: str = os.environ.get("BRIDGE_TOKEN", "")
    bridge_use_https: bool = os.environ.get("BRIDGE_USE_HTTPS", "false").lower() == "true"

    api_key_pepper: str = os.environ.get("API_KEY_PEPPER", "")

    policies_path: str = os.environ.get("POLICIES_PATH", "policies.yaml")
    log_level: str = os.environ.get("LOG_LEVEL", "info")


settings = Settings()
