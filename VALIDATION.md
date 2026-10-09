# Validation — 9 octobre 2026

- Home Assistant 2026.10.0, Python 3.14, pytest-homeassistant-custom-component 0.13.371.
- 43 tests automatisés réussis, sans compte Azaé ni accès à son API.
- Flux utilisateur, doublons, options, reconfiguration et réauthentification vérifiés.
- Chargement/déchargement des plateformes, calendrier, inconnus, disponibilité et diagnostics vérifiés.
- HTTP simulé : payload, en-têtes, rejet des redirections, token en mémoire, retry unique, erreurs et backoff partagé.
- Timer local : expiration du pointage et fin du planning sans requête API supplémentaire.
- Dates : Europe/Paris, passage été/hiver, minuit, intervalle de fin exclusive.
- Présence : séparation du planning, mode pointage optionnel, ancienneté et incohérences.
- Archives : layout `/custom_components/azae`, intégrité ZIP et SHA-256.
- Secrets : fixtures fictives ; aucun identifiant/token réel ni réponse brute dans les livrables.

## Limites

Pas de test sur un compte réel, pas de preuve de présence physique, pas d’exemple
de pointage ouvert en cours confirmé. La complétude/pagination et la signification
exacte de tous les statuts de l’API ne sont pas documentées. Le mode pointage est
une interprétation optionnelle de début renseigné/fin null ou fin récente.
La validation HACS est configurée en excluant le catalogue de marques distant,
car le logo est livré localement pour Home Assistant 2026.3+.
Consulter les checks GitHub pour le résultat des validateurs distants.
