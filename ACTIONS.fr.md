[English version](./ACTIONS.md)

# Actions disponibles

Chaque cle API recoit un ensemble d'actions **par serrure** (`lock_id`) dans
`policies.yaml`. Voici la liste exhaustive des actions comprises par le proxy.

| Action | Ce qu'elle permet | Endpoint(s) concerne(s) |
|---|---|---|
| `battery` | Lire l'etat de la batterie (critique, charge %, en charge) | `GET /v1/locks/{id}/battery`, et les champs batterie dans `GET /v1/locks` |
| `state` | Lire l'etat courant de la serrure (verrouille/deverrouille/...) | `GET /v1/locks/{id}/state`, et le champ state dans `GET /v1/locks` |
| `doorsensor` | Lire l'etat du capteur de porte (ouverte/fermee), si la serrure en a un | `GET /v1/locks/{id}/doorsensor`, et les champs doorsensor dans `GET /v1/locks` |
| `lock` | Envoyer la commande "lock" (verrouiller) | `POST /v1/locks/{id}/action` avec `{"action": "lock"}` |
| `unlock` | Envoyer la commande "unlock" (deverrouiller) | `POST /v1/locks/{id}/action` avec `{"action": "unlock"}` |
| `unlatch` | Envoyer la commande "unlatch" (ouvrir la porte) | `POST /v1/locks/{id}/action` avec `{"action": "unlatch"}` |

## Fonctionnement des grants

- Les actions sont independantes: `lock` et `unlock` sont deux permissions
  separees, pas une seule permission "peut appeler /action". Une cle peut
  avoir le droit de verrouiller une porte sans avoir le droit de la deverrouiller.
- Les grants sont scopes par serrure: une cle peut avoir des actions
  differentes sur la serrure A et la serrure B (ou aucun acces a B).
- Une serrure sans aucune action accordee n'apparait pas dans `GET /v1/locks`
  pour cette cle.
- `GET /v1/locks` ne renvoie que les champs que la cle a le droit de voir
  (ex: pas de `batteryChargeState` si l'action `battery` n'est pas accordee).

## Exemple

```yaml
grants:
  - lock_id: "111"
    actions: ["battery", "state"]   # lecture seule sur la serrure 111
  - lock_id: "222"
    actions: ["lock", "unlock"]     # peut lock/unlock 222, mais pas lire son etat
```

## Pas encore couvert par les grants

- Restrictions horaires (ex: "unlock uniquement 9h-18h").
- Limitation de frequence (ex: "max 3 unlock par jour").
- Rien au-dela des 6 actions ci-dessus (pas de mode "acces a l'endpoint
  seulement" - chaque action est explicite).

Voir le [README](./README.fr.md) principal pour generer et revoquer des cles.
