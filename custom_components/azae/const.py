"""Constants; no account-specific defaults."""
DOMAIN = "azae"
BASE_URL = "https://prod-back.ext.a2micile.com/api"
DEFAULTS = {
    "token_path": "/data/user/token",
    "events_path": "",
    "start_path": "/start",
    "end_path": "/end",
    "clock_in_path": "/heure_pointage_debut",
    "clock_out_path": "/heure_pointage_fin",
    "timezone": "Europe/Paris",
    "poll_seconds": 300,
    "presence_mode": "unknown",
    "evidence_hours": 8,
    "label_filter": "ménage",
}
