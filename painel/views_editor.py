import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import VideoTemplate, Produto

@login_required
def editor_visual(request, template_id):
    template = get_object_or_404(VideoTemplate, pk=template_id)
    
    # Tenta pegar um produto que use esse template para dar realismo ao editor
    produto_exemplo = Produto.objects.filter(template_video=template).first()
    
    # Se não tiver, pega qualquer um
    if not produto_exemplo:
        produto_exemplo = Produto.objects.first()
        
    # Se o banco estiver vazio, cria um objeto dummy em memória
    if not produto_exemplo:
        class DummyProduto:
            descricao = "NOME DO PRODUTO"
            preco = 99.90
            imagem = None
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