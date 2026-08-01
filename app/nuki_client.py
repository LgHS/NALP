"""
Client pour l'API HTTP du Nuki Bridge, en mode "hashToken".

Au lieu d'envoyer le token en clair (?token=xxx), on envoie a chaque appel:
    ts   = timestamp UTC courant, format YYYY-MM-DDTHH:MM:SSZ
    rnr  = entier aleatoire 0-65535
    hash = sha256(f"{ts},{rnr},{token}")

Le Bridge recalcule ce hash de son cote et rejette la requete si le timestamp
est trop vieux (anti-replay) ou si le hash ne correspond pas.
Reference: https://developer.nuki.io/t/hashed-token/14598
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone
from typing import Any

import httpx

# Actions Nuki Bridge (/lockAction) -> notre vocabulaire cote proxy
ACTION_MAP = {
    "unlock": 1,
    "lock": 2,
    "unlatch": 3,
}


class NukiBridgeError(Exception):
    pass


class NukiBridgeClient:
    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        use_https: bool = False,
        timeout: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.scheme = "https" if use_https else "http"
        self.timeout = timeout
        # trust_env=False: le Bridge est un device local, on ne veut jamais
        # router ces appels via un HTTP_PROXY/ALL_PROXY defini dans l'environnement.
        self._client = httpx.Client(timeout=timeout, trust_env=False)

    def _hash_params(self) -> dict[str, Any]:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rnr = random.randint(0, 65535)
        raw = f"{ts},{rnr},{self.token}"
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return {"ts": ts, "rnr": rnr, "hash": h}

    def _url(self, path: str, extra_params: dict[str, Any] | None = None) -> str:
        params = self._hash_params()
        if extra_params:
            params.update(extra_params)
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.scheme}://{self.host}:{self.port}/{path.lstrip('/')}?{query}"

    def _get(self, path: str, extra_params: dict[str, Any] | None = None) -> Any:
        url = self._url(path, extra_params)
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise NukiBridgeError(f"Bridge a repondu {e.response.status_code} sur {path}") from e
        except httpx.RequestError as e:
            raise NukiBridgeError(f"Bridge injoignable ({self.host}:{self.port}): {e}") from e

    def list_locks(self) -> list[dict[str, Any]]:
        """GET /list - tous les locks connus du Bridge, avec leur lastKnownState."""
        return self._get("list")

    def get_lock_state(self, nuki_id: str, device_type: int = 0) -> dict[str, Any]:
        """GET /lockState - interroge l'etat courant d'une serrure."""
        return self._get("lockState", {"nukiId": nuki_id, "deviceType": device_type})

    def get_battery(self, nuki_id: str) -> dict[str, Any]:
        """Pas d'endpoint dedie: on lit lastKnownState depuis /list."""
        for lock in self.list_locks():
            if str(lock.get("nukiId")) == str(nuki_id):
                state = lock.get("lastKnownState", {}) or {}
                return {
                    "batteryCritical": state.get("batteryCritical"),
                    "batteryChargeState": state.get("batteryChargeState"),
                    "batteryCharging": state.get("batteryCharging"),
                }
        raise NukiBridgeError(f"Lock {nuki_id} introuvable sur le Bridge")

    def get_doorsensor(self, nuki_id: str) -> dict[str, Any]:
        """Pas d'endpoint dedie: on lit lastKnownState depuis /list."""
        for lock in self.list_locks():
            if str(lock.get("nukiId")) == str(nuki_id):
                state = lock.get("lastKnownState", {}) or {}
                return {
                    "doorsensorState": state.get("doorsensorState"),
                    "doorsensorStateName": state.get("doorsensorStateName"),
                }
        raise NukiBridgeError(f"Lock {nuki_id} introuvable sur le Bridge")

    def lock_action(self, nuki_id: str, action: str, device_type: int = 0) -> dict[str, Any]:
        """GET /lockAction - envoie une action (lock/unlock/unlatch)."""
        if action not in ACTION_MAP:
            raise ValueError(f"Action inconnue: {action}")
        return self._get(
            "lockAction",
            {"nukiId": nuki_id, "deviceType": device_type, "action": ACTION_MAP[action]},
        )
