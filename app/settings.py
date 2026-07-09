"""Persistent, admin-editable system settings.

Settings are stored as a small key/value table so the admin can tune the
system at runtime (system name, risk threshold, upload limits, etc.) without
editing config.py. Every key has a typed default declared here, so the app
keeps working even before the table is seeded.
"""
from flask import current_app

from app import db
from app.models import SystemSetting
from app.utils import utcnow

SETTINGS = [
    {
        "key": "app_name",
        "label": "System Name",
        "type": "string",
        "default": "Smart Water Point Monitoring System",
        "description": "Name shown on exported reports and notifications.",
    },
    {
        "key": "admin_email",
        "label": "Admin Contact Email",
        "type": "string",
        "default": "admin@smartwater.rw",
        "description": "Contact address surfaced to users.",
    },
    {
        "key": "risk_threshold",
        "label": "At-Risk Probability Threshold",
        "type": "float",
        "default": 0.5,
        "description": "A water point with risk probability above this is classified 'At Risk'.",
    },
    {
        "key": "session_cookie_secure",
        "label": "Secure Cookies (HTTPS only)",
        "type": "bool",
        "default": False,
        "description": "Only transmit the session cookie over HTTPS connections.",
    },
    {
        "key": "max_upload_mb",
        "label": "Max Upload Size (MB)",
        "type": "int",
        "default": 16,
        "description": "Maximum size allowed for uploaded data files.",
    },
    {
        "key": "default_district",
        "label": "Default District",
        "type": "string",
        "default": "Bugesera",
        "description": "District pre-selected when uploading new water point data.",
    },
]

# Settings pushed into Flask's app config so the rest of the code (reports,
# session handling, upload limits) picks them up automatically.
_CONFIG_MAPPING = {
    "app_name": "APP_NAME",
    "admin_email": "ADMIN_EMAIL",
    "session_cookie_secure": "SESSION_COOKIE_SECURE",
    "max_upload_mb": "MAX_CONTENT_LENGTH",
}


def _cast(value_type, raw):
    if raw is None:
        return None
    if value_type == "int":
        return int(raw)
    if value_type == "float":
        return float(raw)
    if value_type == "bool":
        return str(raw).strip().lower() in ("1", "true", "t", "yes")
    return raw


def _default_for(key):
    for definition in SETTINGS:
        if definition["key"] == key:
            return definition["default"]
    return None


def ensure_defaults():
    """Insert any setting rows that don't yet exist. Idempotent."""
    for definition in SETTINGS:
        if not SystemSetting.query.filter_by(key=definition["key"]).first():
            db.session.add(
                SystemSetting(
                    key=definition["key"],
                    value=str(definition["default"]),
                    value_type=definition["type"],
                    description=definition["description"],
                )
            )
    db.session.commit()


def get_setting(key, default=None):
    setting = SystemSetting.query.filter_by(key=key).first()
    if setting is None:
        fallback = _default_for(key)
        return fallback if fallback is not None else default
    return _cast(setting.value_type, setting.value)


def set_setting(key, value):
    setting = SystemSetting.query.filter_by(key=key).first()
    if setting is None:
        definition = next((d for d in SETTINGS if d["key"] == key), None)
        setting = SystemSetting(key=key, value_type=definition["type"] if definition else "string")
        db.session.add(setting)
    setting.value = str(value)
    setting.updated_at = utcnow()
    db.session.commit()


def all_settings():
    ensure_defaults()
    return [{**definition, "value": get_setting(definition["key"])} for definition in SETTINGS]


def apply_settings_to_config():
    """Sync persisted settings into Flask config for the current request."""
    for key, config_key in _CONFIG_MAPPING.items():
        value = get_setting(key)
        if key == "max_upload_mb":
            current_app.config[config_key] = int(value) * 1024 * 1024
        else:
            current_app.config[config_key] = value
    current_app.config["DEFAULT_DISTRICT"] = get_setting("default_district", "Bugesera")
