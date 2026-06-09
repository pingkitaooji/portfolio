import logging

from django.views.csrf import csrf_failure

from .auth_logging import request_meta


logger = logging.getLogger("reports.csrf")


def csrf_failure_view(request, reason=""):
    meta = request_meta(request)
    username = request.POST.get("username", "-") if request.method == "POST" else "-"
    logger.warning(
        "LOGIN_CSRF_FAILURE username=%s ip=%s host=%s path=%s reason=%s referer=%s origin=%s ua=%s",
        username,
        meta["ip"],
        meta["host"],
        meta["path"],
        reason,
        request.META.get("HTTP_REFERER", "-"),
        request.META.get("HTTP_ORIGIN", "-"),
        meta["user_agent"],
    )
    return csrf_failure(request, reason=reason)
