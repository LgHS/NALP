[Version francaise](./ACTIONS.fr.md)

# Available actions

Each API key is granted a set of actions **per lock** (`lock_id`) in
`policies.yaml`. This is the exhaustive list of actions the proxy understands.

| Action | What it allows | Endpoint(s) gated |
|---|---|---|
| `battery` | Read battery status (critical flag, charge %, charging) | `GET /v1/locks/{id}/battery`, and the battery fields in `GET /v1/locks` |
| `state` | Read the current lock state (locked/unlocked/...) | `GET /v1/locks/{id}/state`, and the state field in `GET /v1/locks` |
| `doorsensor` | Read the door sensor state (open/closed), if the lock has one | `GET /v1/locks/{id}/doorsensor`, and the doorsensor fields in `GET /v1/locks` |
| `lock` | Send the "lock" command | `POST /v1/locks/{id}/action` with `{"action": "lock"}` |
| `unlock` | Send the "unlock" command | `POST /v1/locks/{id}/action` with `{"action": "unlock"}` |
| `unlatch` | Send the "unlatch" (open the door) command | `POST /v1/locks/{id}/action` with `{"action": "unlatch"}` |

## How grants work

- Actions are independent: `lock` and `unlock` are two separate grants, not
  one "can call /action" permission. A key can be allowed to lock a door but
  denied from unlocking it.
- Grants are scoped per lock: a key can have different actions on lock A than
  on lock B (or no access at all to lock B).
- A lock with zero granted actions won't appear in `GET /v1/locks` for that key.
- `GET /v1/locks` only returns the fields the key is allowed to see (e.g. no
  `batteryChargeState` if the `battery` action isn't granted).

## Example

```yaml
grants:
  - lock_id: "111"
    actions: ["battery", "state"]   # read-only on lock 111
  - lock_id: "222"
    actions: ["lock", "unlock"]     # can lock/unlock 222, but can't read its state
```

## Not covered by grants (yet)

- Time-based restrictions (e.g. "unlock only between 9am-6pm").
- Rate limiting (e.g. "max 3 unlocks per day").
- Anything beyond the 6 actions above (there's no per-endpoint-only mode -
  every action is explicit).

See the main [README](./README.md) for how to generate and revoke keys.
