"""
Hashing des cles API distribuees par le proxy (pas le token du Bridge).

On ne stocke jamais une cle en clair dans policies.yaml, seulement
sha256(pepper + cle). Le pepper vit uniquement en variable d'env, jamais
dans le fichier de policies -> si policies.yaml fuit seul, les hashs sont
inutilisables sans le pepper.
"""

from __future__ import annotations

import hashlib
import hmac

from app.config import settings


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(f"{settings.api_key_pepper}{raw_token}".encode("utf-8")).hexdigest()


def verify_token(raw_token: str, stored_hash: str) -> bool:
    computed = hash_token(raw_token)
    return hmac.compare_digest(computed, stored_hash)
