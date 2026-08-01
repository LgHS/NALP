[Version francaise](./README.fr.md)

# Nuki Proxy

A small local proxy that sits between the Nuki Bridge API and your clients
(third-party apps, guests, your own services), to give granular access
instead of the single Bridge token that grants everything.

- The proxy is the only thing that knows the real Bridge token, and talks to
  it using **hashToken** (never the plain token) to limit secret exposure.
- Each client gets its own API key, scoped by lock and by action
  (`battery`, `state`, `doorsensor`, `lock`, `unlock`, `unlatch`), with optional expiry.
- No key is ever stored in plaintext: only its hash (salted with a pepper)
  lives in `policies.yaml`.

> This repo is public: `.env` and `policies.yaml` (which hold your real
> secrets/hashes once configured) are in `.gitignore` and must never be
> committed. Only `.env.example` and `policies.example.yaml` are versioned.

## Getting started

1. Copy `.env.example` to `.env` and fill in:
   - `BRIDGE_HOST` / `BRIDGE_PORT`: your Bridge's local IP and port
   - `BRIDGE_TOKEN`: the Bridge API token (visible in the Nuki app, developer mode)
   - `API_KEY_PEPPER`: a random string generated once (`openssl rand -hex 32`),
     never change it again once keys have been issued

2. Copy `policies.example.yaml` to `policies.yaml` and remove the example entry.

3. Generate a key for a user:

   ```bash
   export API_KEY_PEPPER=<same pepper as in .env>
   python3 generate_key.py --name "Marie (guest)" \
       --lock <nukiId> --actions battery,state --expires-days 7
   ```

   This prints the plaintext key (give it to the user once, don't store it)
   and the corresponding YAML block (with the hash) to paste into `policies.yaml`.

4. Run it:

   ```bash
   docker compose up -d --build
   ```

The proxy listens on `http://<host>:8000`.

## Exposed API

All routes require `Authorization: Bearer <key>`.

- `GET /v1/locks` - locks visible to this key, fields filtered by granted actions
- `GET /v1/locks/{id}/state` - requires the `state` grant
- `GET /v1/locks/{id}/battery` - requires the `battery` grant
- `GET /v1/locks/{id}/doorsensor` - requires the `doorsensor` grant
- `POST /v1/locks/{id}/action` `{"action": "lock"|"unlock"|"unlatch"}` -
  requires the matching grant
- `GET /healthz` - no auth, for monitoring

Rejections: `401` if the key is missing/invalid/expired, `403` if the
action/lock isn't in the grants, `502` if the Bridge doesn't respond.

See [ACTIONS.md](./ACTIONS.md) for the full list of grantable actions.

## Revoking a key

Remove its entry from `policies.yaml` and restart the container
(`docker compose restart`), or add a hot-reload admin endpoint later.

## Testing without real hardware

A fake Bridge is provided in `tests/fake_bridge.py`, implementing
`/list`, `/lockState`, `/lockAction` with the same hashToken verification
as the real Bridge:

```bash
python3 tests/fake_bridge.py --port 9090 --token testtoken123
# in another terminal, with BRIDGE_HOST=127.0.0.1 BRIDGE_PORT=9090
# BRIDGE_TOKEN=testtoken123 to point the proxy at it
```

## Known limitations / possible improvements

- No rate limiting on auth (add one if exposed beyond the LAN).
- No hot-reload of `policies.yaml` (requires a proxy restart).
- `BRIDGE_USE_HTTPS` assumes a valid certificate; adjust if the Bridge uses
  a self-signed one.
- The Bridge itself isn't on TLS: ideally isolate it on its own
  VLAN/network segment that only the proxy can reach.
