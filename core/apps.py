import json
import time
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        # #region agent log
        from django.conf import settings
        log_path = getattr(settings, 'DEBUG_LOG_PATH', None)
        if log_path:
            try:
                payload = {
                    "sessionId": "debug-session",
                    "runId": "startup",
                    "hypothesisId": "A",
                    "location": "core/apps.py:ready",
                    "message": "EMAIL_BACKEND at startup",
                    "data": {"EMAIL_BACKEND": getattr(settings, 'EMAIL_BACKEND', ''), "EMAIL_HOST": getattr(settings, 'EMAIL_HOST', '')},
                    "timestamp": int(time.time() * 1000),
                }
                with open(log_path, "a") as f:
                    f.write(json.dumps(payload) + "\n")
            except Exception:
                pass
        # #endregion
        import core.signals  # noqa
