"""
Chargement et interrogation de policies.yaml.

Format:
    api_keys:
      - name: "Marie"
        token_hash: "<sha256(pepper + token)>"
        expires_at: "2026-12-31T00:00:00Z"  # ou null = pas d'expiration
        grants:
          - lock_id: "12345678"
            actions: ["battery", "state"]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import yaml

from app.auth import verify_token
from app.config import settings


@dataclass
class Grant:
    lock_id: str
    actions: set[str] = field(default_factory=set)


@dataclass
class ApiKeyEntry:
    name: str
    token_hash: str
    expires_at: datetime | None
    grants: dict[str, Grant]  # lock_id -> Grant

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    def allows(self, lock_id: str, action: str) -> bool:
        if self.is_expired():
            return False
        grant = self.grants.get(str(lock_id))
        return grant is not None and action in grant.actions

    def visible_locks(self) -> list[str]:
        if self.is_expired():
            return []
        return [lock_id for lock_id, g in self.grants.items() if g.actions]


def _parse_expiry(raw: str | datetime | None) -> datetime | None:
    if not raw:
        return None
    # PyYAML convertit automatiquement les chaines ISO8601 en datetime,
    # mais on accepte aussi une chaine brute au cas ou (ex: quotee dans le yaml).
    dt = raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class PolicyStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._entries: list[ApiKeyEntry] = []
        self.reload()

    def reload(self) -> None:
        with open(self.path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        entries = []
        for item in raw.get("api_keys", []):
            grants = {
                str(g["lock_id"]): Grant(lock_id=str(g["lock_id"]), actions=set(g.get("actions", [])))
                for g in item.get("grants", [])
            }
            entries.append(
                ApiKeyEntry(
                    name=item["name"],
                    token_hash=item["token_hash"],
                    expires_at=_parse_expiry(item.get("expires_at")),
                    grants=grants,
                )
            )
        self._entries = entries

    def find_by_token(self, raw_token: str) -> ApiKeyEntry | None:
        for entry in self._entries:
            if verify_token(raw_token, entry.token_hash):
                return entry
        return None


policy_store = PolicyStore(settings.policies_path)
