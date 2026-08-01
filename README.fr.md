[English version](./README.md)

# Nuki Proxy

Petit proxy local qui se met entre l'API du Nuki Bridge et tes clients
(apps tierces, invites, tes propres services), pour donner des acces
granulaires au lieu du token Bridge unique qui donne tout.

- Le proxy est le seul a connaitre le vrai token du Bridge, et lui parle en
  **hashToken** (jamais en token clair) pour limiter l'exposition du secret.
- Chaque client recoit sa propre cle API, scopee par serrure et par action
  (`battery`, `state`, `lock`, `unlock`, `unlatch`), avec expiration optionnelle.
- Aucune cle n'est stockee en clair: seul son hash (sale par un pepper) vit
  dans `policies.yaml`.

> Ce repo est public: `.env` et `policies.yaml` (qui contiennent tes vrais
> secrets/hash une fois configures) sont dans `.gitignore` et ne doivent
> jamais etre commit. Seuls `.env.example` et `policies.example.yaml` sont
> versionnes.

## Demarrage

1. Copier `.env.example` en `.env` et renseigner:
   - `BRIDGE_HOST` / `BRIDGE_PORT`: IP locale et port de ton Bridge
   - `BRIDGE_TOKEN`: le token API du Bridge (visible dans l'app Nuki, mode developpeur)
   - `API_KEY_PEPPER`: une chaine aleatoire generee une fois (`openssl rand -hex 32`),
     a ne plus jamais changer une fois des cles distribuees

2. Copier `policies.example.yaml` en `policies.yaml` et supprimer l'entree d'exemple.

3. Generer une cle pour un utilisateur:

   ```bash
   export API_KEY_PEPPER=<le meme pepper que dans .env>
   python3 generate_key.py --name "Marie (invitee)" \
       --lock <nukiId> --actions battery,state --expires-days 7
   ```

   Ca affiche la cle en clair (a donner une seule fois a l'utilisateur) et le
   bloc YAML correspondant (avec le hash) a coller dans `policies.yaml`.

4. Lancer:

   ```bash
   docker compose up -d --build
   ```

Le proxy ecoute sur `http://<host>:8000`.

## API exposee

Toutes les routes necessitent `Authorization: Bearer <cle>`.

- `GET /v1/locks` - liste des serrures visibles pour cette cle, champs filtres
  selon les actions accordees
- `GET /v1/locks/{id}/state` - necessite le grant `state`
- `GET /v1/locks/{id}/battery` - necessite le grant `battery`
- `POST /v1/locks/{id}/action` `{"action": "lock"|"unlock"|"unlatch"}` -
  necessite le grant correspondant
- `GET /healthz` - pas d'auth, pour le monitoring

Refus: `401` si cle absente/invalide/expiree, `403` si l'action/serrure n'est
pas dans les grants, `502` si le Bridge ne repond pas.

## Revoquer une cle

Supprimer son entree dans `policies.yaml` et redemarrer le container
(`docker compose restart`), ou recharger a chaud si tu ajoutes un endpoint
admin plus tard.

## Tester sans le vrai hardware

Un faux Bridge est fourni dans `tests/fake_bridge.py`, il implemente
`/list`, `/lockState`, `/lockAction` avec la meme verification hashToken
que le vrai Bridge:

```bash
python3 tests/fake_bridge.py --port 9090 --token testtoken123
# dans un autre terminal, avec BRIDGE_HOST=127.0.0.1 BRIDGE_PORT=9090
# BRIDGE_TOKEN=testtoken123 pour pointer le proxy dessus
```

## Limites connues / a ameliorer

- Pas de rate limiting sur l'auth (a ajouter si expose au-dela du LAN).
- Pas de reload a chaud de `policies.yaml` (necessite un restart du proxy).
- `BRIDGE_USE_HTTPS` suppose un certificat valide; a adapter si le Bridge
  utilise un certificat auto-signe.
- Le Bridge lui-meme n'est pas en TLS: isoler idealement le Bridge sur un
  VLAN/segment reseau dont seul le proxy peut s'approcher.
