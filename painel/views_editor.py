import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import VideoTemplate, Produto

@login_required
def editor_visual(request, template_id):
    template = get_object_or_404(VideoTemplate, pk=template_id)
    
    # 1. Tenta pegar UM produto real que use este template
    produto_real = Produto.objects.filter(template_video=template).first()
    
    # 2. Se achou, usa ele. Se NÃO achou, cria um Dummy (falso)
    if produto_real:
        produto_exemplo = produto_real
    else:
        # Objeto falso apenas para visualização no editor
        class DummyProduto:
            descricao = "NOME DO PRODUTO (MODELO)"
            preco = 0.00
            imagem = None # Não tem imagem
        produto_exemplo = DummyProduto()

    return render(request, 'painel/editor_visual.html', {
        'template': template,
        'produto': produto_exemplo
    })

@csrf_exempt
@login_required
def salvar_layout(request, template_id):
    if request.method == "POST":
        template = get_object_or_404(VideoTemplate, pk=template_id)
        data = json.loads(request.body)

        # Atualiza campos nativos
        template.titulo_top = data.get('titulo_top')
        template.titulo_left = data.get('titulo_left')
        template.preco_top = data.get('preco_top')
        template.preco_left = data.get('preco_left')
        
        # Imagem
        img_data = data.get('imagem_config', {})
        template.img_top = img_data.get('top', template.img_top)
        template.img_left = img_data.get('left', template.img_left)
        template.img_width = img_data.get('width', template.img_width)

        # Atualiza JSONs
        template.estilos_css = data.get('estilos_css', {})
        template.elementos_extras = data.get('elementos_extras', [])
        
        template.save()
        return JsonResponse({"status": "success"})
    
    return JsonResponse({"status": "error"}, status=400)