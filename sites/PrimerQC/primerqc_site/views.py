import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .prediction import predict_primer_pair


@require_POST
def predict(request):
    """Expose the Python PrimerQC scorer to the browser interface."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
        result = predict_primer_pair(
            payload.get("forward_primer"),
            payload.get("reverse_primer"),
            payload.get("amplicon_length_bp"),
        )
    except json.JSONDecodeError:
        return JsonResponse({"error": "請提供有效的 JSON。"}, status=400)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(result)
