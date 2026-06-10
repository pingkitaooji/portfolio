import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .analysis import analyze_signals


@require_POST
def analyze(request):
    """Expose the Python qPCR analysis engine to the interactive frontend."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
        result = analyze_signals(payload.get("signals"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(result)
