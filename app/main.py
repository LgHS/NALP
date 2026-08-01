from __future__ import annotations

import logging
import sys

from fastapi import Depends, FastAPI, HTTPException, Header
from pydantic import BaseModel

from app.config import settings
from app.nuki_client import NukiBridgeClient, NukiBridgeError
from app.policies import ApiKeyEntry, policy_store

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("nuki_proxy")

if not settings.bridge_host or not settings.bridge_token:
    raise RuntimeError("BRIDGE_HOST et BRIDGE_TOKEN doivent etre definis (voir .env.example)")

app = FastAPI(title="Nuki Proxy", version="0.1.0")

bridge = NukiBridgeClient(
    host=settings.bridge_host,
    port=settings.bridge_port,
    token=settings.bridge_token,
    use_https=settings.bridge_use_https,
)


def get_current_key(authorization: str | None = Header(default=None)) -> ApiKeyEntry:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization: Bearer <token> manquant")

    raw_token = authorization.removeprefix("Bearer ").strip()
    entry = policy_store.find_by_token(raw_token)

    if entry is None:
        log.warning("auth refusee: token inconnu")
        raise HTTPException(status_code=401, detail="Token invalide")

    if entry.is_expired():
        log.warning("auth refusee: token expire (name=%s)", entry.name)
        raise HTTPException(status_code=401, detail="Token expire")

    return entry


def require_grant(entry: ApiKeyEntry, lock_id: str, action: str) -> None:
    if not entry.allows(lock_id, action):
        log.warning(
            "acces refuse: name=%s lock_id=%s action=%s", entry.name, lock_id, action
        )
        raise HTTPException(status_code=403, detail=f"Action '{action}' non autorisee sur ce lock")
    log.info("acces autorise: name=%s lock_id=%s action=%s", entry.name, lock_id, action)


class LockActionRequest(BaseModel):
    action: str  # "lock" | "unlock" | "unlatch"


@app.get("/v1/locks")
def list_locks(entry: ApiKeyEntry = Depends(get_current_key)):
    visible = set(entry.visible_locks())
    if not visible:
        return {"locks": []}
    try:
        all_locks = bridge.list_locks()
    except NukiBridgeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    result = []
    for lock in all_locks:
        lock_id = str(lock.get("nukiId"))
        if lock_id not in visible:
            continue
        grant = entry.grants[lock_id]
        item = {"lock_id": lock_id, "name": lock.get("name")}
        state = lock.get("lastKnownState", {}) or {}
        if "state" in grant.actions:
            item["state"] = state.get("stateName")
        if "battery" in grant.actions:
            item["batteryCritical"] = state.get("batteryCritical")
            item["batteryChargeState"] = state.get("batteryChargeState")
        if "doorsensor" in grant.actions:
            item["doorsensorState"] = state.get("doorsensorState")
            item["doorsensorStateName"] = state.get("doorsensorStateName")
        result.append(item)
    return {"locks": result}


@app.get("/v1/locks/{lock_id}/state")
def get_state(lock_id: str, entry: ApiKeyEntry = Depends(get_current_key)):
    require_grant(entry, lock_id, "state")
    try:
        state = bridge.get_lock_state(lock_id)
    except NukiBridgeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return state


@app.get("/v1/locks/{lock_id}/battery")
def get_battery(lock_id: str, entry: ApiKeyEntry = Depends(get_current_key)):
    require_grant(entry, lock_id, "battery")
    try:
        battery = bridge.get_battery(lock_id)
    except NukiBridgeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return battery


@app.get("/v1/locks/{lock_id}/doorsensor")
def get_doorsensor(lock_id: str, entry: ApiKeyEntry = Depends(get_current_key)):
    require_grant(entry, lock_id, "doorsensor")
    try:
        doorsensor = bridge.get_doorsensor(lock_id)
    except NukiBridgeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return doorsensor


@app.post("/v1/locks/{lock_id}/action")
def do_action(lock_id: str, body: LockActionRequest, entry: ApiKeyEntry = Depends(get_current_key)):
    if body.action not in ("lock", "unlock", "unlatch"):
        raise HTTPException(status_code=400, detail="action doit etre lock, unlock ou unlatch")
    require_grant(entry, lock_id, body.action)
    try:
        result = bridge.lock_action(lock_id, body.action)
    except NukiBridgeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return result


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
