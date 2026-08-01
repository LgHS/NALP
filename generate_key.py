#!/usr/bin/env python3
"""
Genere une nouvelle cle API pour un user/app tierce.

Affiche:
  - la cle en clair -> a donner UNE FOIS a l'utilisateur, ne la garde pas
  - le bloc YAML a coller dans policies.yaml (avec le hash, pas la cle)

Usage:
    python3 generate_key.py --name "Marie (invitee)" \
        --lock 12345678 --actions battery,state \
        [--expires-days 7]

Necessite que API_KEY_PEPPER soit deja defini dans l'environnement
(le meme que celui utilise par le proxy en prod), sinon le hash genere
ne correspondra pas a celui que le proxy recalculera.
"""

from __future__ import annotations

import argparse
import os
import secrets
from datetime import datetime, timedelta, timezone

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.auth import hash_token  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Genere une cle API scopee pour le proxy Nuki")
    parser.add_argument("--name", required=True, help="Nom/description de l'utilisateur ou service")
    parser.add_argument("--lock", action="append", required=True, dest="locks",
                         help="nukiId d'une serrure concernee (repeter pour plusieurs serrures)")
    parser.add_argument("--actions", required=True,
                         help="actions autorisees separees par des virgules, ex: battery,state")
    parser.add_argument("--expires-days", type=int, default=None,
                         help="expiration en jours (par defaut: pas d'expiration)")
    args = parser.parse_args()

    if not os.environ.get("API_KEY_PEPPER"):
        print("ATTENTION: API_KEY_PEPPER n'est pas defini dans l'environnement.", file=sys.stderr)
        print("Le hash genere ne correspondra pas a celui utilise par le proxy en prod.", file=sys.stderr)

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    actions = [a.strip() for a in args.actions.split(",") if a.strip()]

    expires_at = None
    if args.expires_days is not None:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=args.expires_days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    print("=" * 60)
    print("CLE EN CLAIR (a donner une seule fois, ne pas la stocker) :")
    print(raw_token)
    print("=" * 60)
    print()
    print("A coller dans policies.yaml sous api_keys:")
    print()
    print(f'  - name: "{args.name}"')
    print(f'    token_hash: "{token_hash}"')
    print(f"    expires_at: {expires_at if expires_at else 'null'}")
    print("    grants:")
    for lock_id in args.locks:
        print(f'      - lock_id: "{lock_id}"')
        print(f"        actions: {actions}")


if __name__ == "__main__":
    main()
