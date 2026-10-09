# HA Azaé

![Logo Azaé](custom_components/azae/brand/logo.png)

Intégration personnalisée non officielle, version 0.1.0, conçue et testée sur
Home Assistant **2026.10.0** (Python 3.14). Installation manuelle immédiate ;
dépôt GitHub : **[pierrec18/ha-azae](https://github.com/pierrec18/ha-azae)**.
Les tests sont simulés : aucune requête n’a été envoyée à un compte réel Azaé.

## Ce que l’intégration indique

| Entité (nom proposé) | Signification |
| --- | --- |
| `binary_sensor.azae_presence_declaree` | Présence **déclarée**, jamais une mesure physique ; `unknown` par défaut. |
| `binary_sensor.azae_intervention_planifiee` | `on` pendant un intervalle issu du planning ; aucune conclusion sur la présence. |
| `calendar.azae_interventions` | Calendrier des interventions, en lecture seule. Les titres sont génériques. |

Home Assistant peut modifier ces identifiants si des entités du même nom existent.
L’intervalle du planning est `[début, fin[` : la fin est exclue. Des interventions
qui chevauchent minuit ou se chevauchent entre elles sont acceptées.
Une liste vide reconnue signifie « aucune intervention planifiée » et **ne signifie
pas « personne absente »**. Une réponse non reconnue rend les deux capteurs `unknown`
et le calendrier indisponible ; un échec réseau/authentification rend les entités
`unavailable`. Les diagnostics indiquent `schema_ok`, sans exposer la réponse brute.

## Installation manuelle avec le ZIP

1. Sauvegarder votre configuration Home Assistant.
2. Extraire **azae-install-0.1.0.zip** dans le dossier `/config` de Home Assistant.
   Le résultat doit être `/config/custom_components/azae/manifest.json`, sans dossier
   supplémentaire entre `custom_components` et `azae`.
3. Redémarrer Home Assistant.
4. Paramètres → Appareils et services → Ajouter une intégration → **HA Azaé**.
5. Saisir votre e-mail, votre mot de passe actuel, votre code agence et votre
   matricule usager. Ces deux derniers champs sont des textes : conserver les zéros.
   Le chemin du token confirmé par l’exemple est `/data/user/token`.
6. Laisser d’abord la présence en mode `unknown`. Vérifier le calendrier puis consulter
   la section pointage avant d’activer le mode correspondant dans **Options**.

## Installation via HACS

[Ajouter HA Azaé à HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=pierrec18&repository=ha-azae&category=integration)

1. Dans HACS → menu → Dépôts personnalisés, ajouter
   `https://github.com/pierrec18/ha-azae`, type **Intégration**.
2. Télécharger **HA Azaé**, puis redémarrer Home Assistant.
3. Paramètres → Appareils et services → Ajouter une intégration → **HA Azaé**.
4. Saisir vos identifiants et les codes de votre usager.

`hacs.json` télécharge `custom_components/azae` depuis le dépôt ; `zip_release`
n’est pas activé. Les ZIP de la release servent à l’installation manuelle et au
code source. La release GitHub correspond au tag `v0.1.0`.
Ce dépôt personnalisé n’est pas une intégration officielle ni une inclusion dans
le catalogue HACS par défaut.

Le logo provient du [site officiel Azaé](https://www.azae.com/),
[source SVG](https://www.azae.com/wp-content/uploads/2023/03/logo.svg).
Il est intégré au dossier `brand/`, pris en charge nativement par Home Assistant
2026.3 et versions ultérieures. Certains écrans de HACS peuvent encore dépendre
du catalogue de marques distant pour leur vignette ; le logo local est fourni
pour l’interface Home Assistant. Les droits sur le logo restent ceux d’Azaé.

Pour republier un fork, `python scripts/prepare_repository.py COMPTE DEPOT` met
à jour les liens et le propriétaire sans envoyer de données sur Internet.
Les workflows exécutent les tests, hassfest et le validateur HACS ; la vérification
du catalogue distant des marques est exclue au profit du dossier `brand/` local.

## Réponses connues et adaptation

Les seuls schémas confirmés viennent d’exemples transmis par l’utilisateur, sans
spécification publique ni garantie de stabilité :

- `POST https://prod-back.ext.a2micile.com/api/login`, corps JSON `email`, `password`,
  en-tête `client-name: Extranet.Front` ; token dans `/data/user/token`.
- `POST /api/get_liste_heures`, Bearer, corps JSON `type: Usager`, `code_agence`,
  `matricule`, `matricules: null`, `start`, `end` sous forme `YYYY-MM-DD`.
- La réponse d’heures fournie est une **liste à la racine**, avec `start`, `end`,
  `libelle`, `heure_pointage_debut` et `heure_pointage_fin`.
- Les dates de l’exemple sont des chaînes `YYYY-MM-DD HH:MM:SS` sans fuseau.

Les options de chemins utilisent les **pointeurs JSON RFC 6901**, pas des chemins
avec des points. Le chemin vide sélectionne la racine ; `/data/interventions`
sélectionne une liste imbriquée ; `/start` s’applique à chaque ligne.
Aucune recherche automatique de token ni essai de variantes de noms de champs.
Les dates SQL de l’exemple et les dates ISO 8601 avec heure sont prises en charge.
Les autres structures (date et heure séparées, pagination, récurrences non développées,
dates sans heure) nécessitent un adaptateur spécifique : elles ne sont pas inventées.
Il n’existe pas encore de preuve que l’API renvoie toujours une liste complète.
Si elle devient paginée, un schéma différent sera inconnu ; une troncature silencieuse
côté serveur ne peut pas être détectée sans documentation supplémentaire.

| Option | Valeur par défaut |
| --- | --- |
| Token | `/data/user/token` |
| Liste d’interventions | chaîne vide (racine) |
| Début / fin | `/start` / `/end` |
| Pointage début / fin | `/heure_pointage_debut` / `/heure_pointage_fin` |
| Fuseau des dates sans décalage | `Europe/Paris` |
| Actualisation | 300 secondes (réglable de 60 à 3600) |
| Mode présence | `unknown` |
| Validité du pointage | 8 heures (réglable de 1 à 24) |
| Filtre de libellé | `ménage` (recherche sans distinction de casse ; vide = tout) |

Le filtre agit sur **le calendrier et les deux capteurs**. Une ligne avec un commentaire
`commentaire_annulation` non vide est exclue : c’est une interprétation du champ
à vérifier sur vos propres données. Aucun statut non documenté comme `effective`,
`validated`, `not_started` ou `completed` n’est transformé en preuve de présence.
Les lignes retenues sont validées ensemble : une ligne invalide fait passer la liste
entière en inconnu plutôt que d’afficher un planning faussement complet.
Les identités, noms, adresses, commentaires et tokens ne sont pas exposés comme attributs.

## Mode optionnel « pointage »

Ce mode est une **déduction à partir d’un pointage déclaré**, pas une confirmation de
présence au domicile. Un seul exemple terminé et un seul exemple non commencé ont été
fournis ; aucun exemple de pointage ouvert en cours n’a été confirmé.
Activez ce mode uniquement après avoir vérifié que, sur votre compte,
un pointage de début renseigné avec une fin `null` signifie une intervention ouverte.

- `on` : au moins un pointage ouvert, début dans le passé et âgé de moins de la durée
  maximale ; aucune déclaration récente fermée contradictoire.
- `off` : au moins un pointage fermé dont la fin est dans le passé et récente ;
  aucun pointage ouvert contradictoire. Cela signifie « fin déclarée récente »,
  sans garantir une absence physique ni exclure une arrivée non encore remontée.
- `unknown` : absence de pointage, pointage trop ancien, début/fin futur, schéma
  incomplet, conflits entre interventions, ou cache trop ancien.

Une ancienne intervention ouverte rend le résultat inconnu, même si une autre ligne
est fermée. Un champ absent n’est pas assimilé à un champ explicitement `null`.
La présence n’est jamais dérivée de `start`, `end`, `validated` ou `effective`.
Le capteur porte l’attribut `physical_presence_verified: false` et un `reason` technique.
Les raisons possibles sont `no_confirmed_presence_source`, `no_recent_clock`,
`open_clock`, `closed_clock`, `stale_data`, `unsupported_response`, `future_clock`,
`expired_open_clock` et `conflicting_clocks`.

Pour une présence physique vérifiée, il faudra une autre source fiable (capteur local,
confirmation explicite, etc.). Aucune automatisation de sécurité ne doit assimiler
`unknown` ou `unavailable` à `off`. Exemple de condition pour une automatisation
basée volontairement sur une présence **déclarée** :

```yaml
condition:
  - condition: state
    entity_id: binary_sensor.azae_presence_declaree
    state: "on"
```

## Temps, calendrier et rafraîchissement

Toutes les dates sont normalisées en UTC ; les dates sans décalage sont interprétées
selon le fuseau configuré, par défaut Europe/Paris. Le rendu visuel du calendrier
suit le fuseau de Home Assistant : régler aussi celui-ci sur Europe/Paris si souhaité.
Lors des passages été/hiver, une heure locale ambiguë ou inexistante est rejetée ;
un horodatage avec décalage explicite (`+01:00`, `+02:00`, `Z`) lève l’ambiguïté.

Une requête partagée est effectuée toutes les cinq minutes. Le cache principal couvre
les deux jours précédents et les 31 jours à venir. Les bornes de date sont élargies
à chaque requête, car l’inclusivité de `end` n’est pas documentée. Le calendrier
interroge également l’API pour les plages affichées hors de cette fenêtre ;
chaque plage doit être positive et ne pas dépasser 366 jours. Les événements sont
triés et filtrés par chevauchement avec la plage demandée, fin exclusive.
Les titres restent « Intervention Azaé (planning) », même si l’API mélange réalisé
et prévisionnel dans ses heures de début/fin.

Les états sont recalculés localement toutes les 30 secondes, sans nouvelle requête.
La présence et le planning deviennent inconnus si le dernier cache date d’au moins
deux intervalles d’actualisation ; le calendrier devient indisponible.
Une panne d’API rend les entités indisponibles immédiatement au prochain échec détecté.
La commande native `homeassistant.update_entity` permet de demander une actualisation.

Le Bearer reste seulement en mémoire. Après un 401/403, le client refait `/login`
puis réessaie une seule fois ; un nouvel échec demande une réauthentification via
Home Assistant. Aucun endpoint de renouvellement non documenté n’est utilisé.
Un HTTP 429 déclenche un délai partagé entre calendrier et actualisation, basé sur
`Retry-After` numérique, ou cinq minutes sinon. Les redirections HTTP sont refusées.
Le délai réseau est de 20 secondes et TLS reste vérifié.

## Confidentialité

Aucun identifiant réel ni exemple brut partagé n’est inclus dans le dépôt ou les ZIP.
Les fixtures utilisent des données entièrement fictives. Aucun corps de réponse,
token, mot de passe, nom ou adresse n’est journalisé par l’intégration.
Les diagnostics contiennent seulement le succès du rafraîchissement, le statut du
schéma, le nombre d’événements et quelques options non personnelles.

Home Assistant **stocke les identifiants saisis dans son stockage de configuration**,
comme beaucoup d’intégrations cloud ; le champ masqué de l’interface n’est pas un
chiffrement du stockage. Protéger l’accès à `/config` et aux sauvegardes.
Changer le mot de passe dans « Reconfigurer », ou suivre la demande de réauthentification.
Pour changer de compte/usager, supprimer l’entrée et en créer une nouvelle.

## Développement et tests

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest
python scripts/package.py --output-dir ../archives
```

Les tests vérifient le client HTTP simulé, les retries bornés, l’absence de fallback
sur le schéma, les erreurs réseau, les limites API, les changements d’heure,
les bornes du planning, les pointages incohérents/périmés, les flux UI, la création
des entités, les diagnostics, le déchargement et le calendrier à la demande.
Ils n’utilisent aucun accès réel à Azaé. Consulter `VALIDATION.md` pour le résultat
exécuté lors de la livraison et les limites restantes.

Le dépôt complet est disponible dans `azae-source-0.1.0.zip`.
Pour signaler un problème, utiliser les issues du dépôt sans joindre de données personnelles.

## Sources consultées le 9 octobre 2026

- [Home Assistant : config flow](https://developers.home-assistant.io/docs/core/integration/config_flow/)
- [Home Assistant : collecte et DataUpdateCoordinator](https://developers.home-assistant.io/docs/integration_fetching_data/)
- [Home Assistant : calendrier](https://developers.home-assistant.io/docs/core/entity/calendar/)
- [Home Assistant : binary sensor](https://developers.home-assistant.io/docs/core/entity/binary-sensor/)
- [HACS : intégrations](https://www.hacs.dev/docs/publish/integration/)
- [HACS : publication et hacs.json](https://www.hacs.dev/docs/publish/start/)

- [Home Assistant : marques locales](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api/)
