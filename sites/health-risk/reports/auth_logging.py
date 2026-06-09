import logging

from django.contrib.auth.signals import user_logged_in, user_login_failed, user_logged_out
from django.dispatch import receiver


logger = logging.getLogger("reports.auth")


def request_meta(request):
    if request is None:
        return {"ip": "-", "host": "-", "path": "-", "user_agent": "-"}
    try:
        host = request.get_host()
    except Exception:
        host = request.META.get("HTTP_HOST", request.META.get("SERVER_NAME", "-"))
    return {
        "ip": request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "-")).split(",")[0],
        "host": host,
        "path": request.path,
        "user_agent": request.META.get("HTTP_USER_AGENT", "-")[:160],
    }


@receiver(user_logged_in)
def log_user_logged_in(sender, request, user, **kwargs):
    meta = request_meta(request)
    logger.info(
        "LOGIN_SUCCESS username=%s ip=%s host=%s path=%s staff=%s superuser=%s ua=%s",
        user.get_username(),
        meta["ip"],
        meta["host"],
        meta["path"],
        user.is_staff,
        user.is_superuser,
        meta["user_agent"],
    )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    meta = request_meta(request)
    username = credentials.get("username", "-") if credentials else "-"
    logger.warning(
        "LOGIN_FAILED username=%s ip=%s host=%s path=%s reason=invalid_credentials ua=%s",
        username,
        meta["ip"],
        meta["host"],
        meta["path"],
        meta["user_agent"],
    )


@receiver(user_logged_out)
def log_user_logged_out(sender, request, user, **kwargs):
    meta = request_meta(request)
    username = user.get_username() if user else "-"
    logger.info(
        "LOGOUT username=%s ip=%s host=%s path=%s ua=%s",
        username,
        meta["ip"],
        meta["host"],
        meta["path"],
        meta["user_agent"],
    )
