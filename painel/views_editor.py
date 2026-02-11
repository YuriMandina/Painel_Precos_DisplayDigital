import json
import logging

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .models import Midia

logger = logging.getLogger(__name__)

# Views para o editor de estúdio de mídia

@csrf_exempt
@login_required
def salvar_estudio(request, midia_id):
    """
    API para salvar o layout do novo Estúdio de Mídia.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método não permitido"}, status=405)

    midia = get_object_or_404(Midia, pk=midia_id)

    try:
        data = json.loads(request.body)
        midia.dados_estudio = data
        midia.save()
        return JsonResponse({"status": "success"})
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "JSON inválido"}, status=400)
    except Exception as e:
        logger.error(f"Erro ao salvar estúdio {midia_id}: {str(e)}")
        return JsonResponse({"status": "error", "message": "Erro interno"}, status=500)