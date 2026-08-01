"""
Faux Nuki Bridge pour tester le proxy sans le vrai hardware.
Implemente /list et /lockAction avec verification hashToken, comme le vrai Bridge.

Usage: python3 tests/fake_bridge.py --port 9090 --token testtoken123
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Query
import uvicorn

app = FastAPI()
STATE = {
    "token": "testtoken123",
    "locks": {
        "111": {"nukiId": "111", "name": "Porte principale",
                "lastKnownState": {"stateName": "locked", "batteryCritical": False, "batteryChargeState": 87,
                                    "doorsensorState": 2, "doorsensorStateName": "door closed"}},
        "222": {"nukiId": "222", "name": "Porte garage",
                "lastKnownState": {"stateName": "unlocked", "batteryCritical": True, "batteryChargeState": 12,
                                    "doorsensorState": 3, "doorsensorStateName": "door opened"}},
    },
}


def check_hash(ts: str, rnr: int, hash_: str) -> None:
    try:
        ts_dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=401, detail="ts invalide")

    if abs(datetime.now(timezone.utc) - ts_dt) > timedelta(seconds=30):
        raise HTTPException(status_code=401, detail="ts trop ancien (anti-replay)")

    expected = hashlib.sha256(f"{ts},{rnr},{STATE['token']}".encode()).hexdigest()
    if expected != hash_:
        raise HTTPException(status_code=401, detail="hash invalide")


@app.get("/list")
def list_locks(ts: str = Query(...), rnr: int = Query(...), hash: str = Query(...)):
    check_hash(ts, rnr, hash)
    return list(STATE["locks"].values())


@app.get("/lockAction")
def lock_action(
    nukiId: str,
    action: int,
    deviceType: int = 0,
    ts: str = Query(...),
    rnr: int = Query(...),
    hash: str = Query(...),
):
    check_hash(ts, rnr, hash)
    if nukiId not in STATE["locks"]:
        raise HTTPException(status_code=404, detail="lock inconnu")
    new_state = "locked" if action == 2 else "unlocked" if action == 1 else "unlatched"
    STATE["locks"][nukiId]["lastKnownState"]["stateName"] = new_state
    return {"success": True, "state": new_state}


@app.get("/lockState")
def lock_state(
    nukiId: str,
    deviceType: int = 0,
    ts: str = Query(...),
    rnr: int = Query(...),
    hash: str = Query(...),
):
    check_hash(ts, rnr, hash)
    if nukiId not in STATE["locks"]:
        raise HTTPException(status_code=404, detail="lock inconnu")
    return STATE["locks"][nukiId]["lastKnownState"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9090)
    parser.add_argument("--token", default="testtoken123")
    args = parser.parse_args()
    STATE["token"] = args.token
    uvicorn.run(app, host="0.0.0.0", port=args.port)
