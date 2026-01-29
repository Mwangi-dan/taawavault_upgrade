"""
Custom django-allauth account adapter for TaawaVault.
"""
from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    """Account adapter with optional debug instrumentation for email verification."""

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        # #region agent log
        _debug_log(
            location="core/account_adapter.py:send_confirmation_mail",
            message="send_confirmation_mail entered",
            data={"to_email": emailconfirmation.email_address.email, "signup": signup},
            hypothesis_id="C",
        )
        # #endregion
        try:
            super().send_confirmation_mail(request, emailconfirmation, signup)
            # #region agent log
            _debug_log(
                location="core/account_adapter.py:send_confirmation_mail",
                message="send_confirmation_mail completed",
                data={"to_email": emailconfirmation.email_address.email},
                hypothesis_id="B",
            )
            # #endregion
        except Exception as e:
            # #region agent log
            _debug_log(
                location="core/account_adapter.py:send_confirmation_mail",
                message="send_confirmation_mail exception",
                data={"to_email": emailconfirmation.email_address.email, "error_type": type(e).__name__, "error_msg": str(e)},
                hypothesis_id="B",
            )
            # #endregion
            raise


def _debug_log(location, message, data, hypothesis_id):
    import json
    import time
    log_path = getattr(settings, "DEBUG_LOG_PATH", None)
    if not log_path:
        return
    try:
        payload = {
            "sessionId": "debug-session",
            "runId": "signup-flow",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
