import json
import logging
from types import SimpleNamespace

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .models import VideoTemplate, Produto

logger = logging.getLogger(__name__)

@login_required
def editor_visual(request: HttpRequest, template_id: int) -> HttpResponse:
    """
    Renderiza o editor visual (WYSIWYG) para um template específico.
    Usa um produto real ou um dummy para pré-visualização.
    """
    template = get_object_or_404(VideoTemplate, pk=template_id)
    
    # Busca um produto de exemplo para popular o visualizador
    produto_exemplo = Produto.objects.filter(template_video=template).first()
    
    if not produto_exemplo:
        # Cria um objeto simples (Mock) para não quebrar a visualização
        produto_exemplo = SimpleNamespace(
            descricao="NOME DO PRODUTO (MODELO)",
            preco=0.00,
            imagem=None
        )

    context = {
        'template': template,
        'produto': produto_exemplo
    }
    return render(request, 'painel/editor_visual.html', context)


@csrf_exempt
@login_required
def salvar_layout(request: HttpRequest, template_id: int) -> JsonResponse:
    """
    API para salvar as coordenadas e estilos do editor visual via AJAX.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método não permitido"}, status=405)

    template = get_object_or_404(VideoTemplate, pk=template_id)

    try:
        data = json.loads(request.body)
        
        # --- Configuração de Textos ---
        template.titulo_top = data.get('titulo_top', template.titulo_top)
        template.titulo_left = data.get('titulo_left', template.titulo_left)
        template.preco_top = data.get('preco_top', template.preco_top)
        template.preco_left = data.get('preco_left', template.preco_left)
        
        # --- Configuração de Imagem ---
        img_data = data.get('imagem_config', {})
        template.img_top = img_data.get('top', template.img_top)
        template.img_left = img_data.get('left', template.img_left)
        template.img_width = img_data.get('width', template.img_width)

        # --- Estilização Extra ---
        template.estilos_css = data.get('estilos_css', {})
        template.elementos_extras = data.get('elementos_extras', [])
        
        template.save()
        return JsonResponse({"status": "success"})

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "JSON inválido"}, status=400)
    except Exception as e:
        logger.error(f"Erro ao salvar layout do template {template_id}: {str(e)}")
        return JsonResponse({"status": "error", "message": "Erro interno"}, status=500)