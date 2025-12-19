from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Dispositivo, Produto, VideoPropaganda
from .serializers import ProdutoSerializer, DispositivoConfigSerializer

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def parear_dispositivo(request):
    print(f"Tentativa de pareamento recebida: {request.data}")
    
    codigo = request.data.get('codigo', '').strip().upper()
    
    try:
        dispositivo = Dispositivo.objects.get(codigo_acesso=codigo)
        print(f"Sucesso! Dispositivo encontrado: {dispositivo.nome}")
        return Response({"uuid": dispositivo.uuid, "nome": dispositivo.nome})
    except Dispositivo.DoesNotExist:
        print(f"Falha: Código '{codigo}' não existe no banco.")
        return Response({"erro": "Código inválido"}, status=404)

# Serializer simples manual para propaganda (não precisa criar arquivo novo se for simples)
def serializar_propaganda(propaganda):
    return {
        "tipo": "propaganda",
        "url": propaganda.arquivo_video.url,
        "descricao": propaganda.descricao,
        "duracao": propaganda.duracao
    }

@api_view(['GET'])
@permission_classes([AllowAny])
def dados_painel(request, device_uuid):
    dispositivo = get_object_or_404(Dispositivo, uuid=device_uuid)
    
    # ... (lógica de título mantida) ...
    titulo_exibicao = dispositivo.titulo_exibicao if hasattr(dispositivo, 'titulo_exibicao') else ""

    response_data = {
        "config": {
            **DispositivoConfigSerializer(dispositivo).data,
            "titulo_exibicao": titulo_exibicao
        },
        "produtos": [],
        "playlist_final": []
    }

    # Query Produtos (Só os ativos)
    query_produtos = Produto.objects.filter(exibir_no_painel=True)
    familias_alvo = dispositivo.familias.all() if hasattr(dispositivo, 'familias') else None
    if familias_alvo and familias_alvo.exists():
        query_produtos = query_produtos.filter(familia__in=familias_alvo)
    
    # Serializa todos (para a tabela)
    serializer = ProdutoSerializer(query_produtos, many=True, context={'request': request})
    dados_produtos = serializer.data
    response_data["produtos"] = dados_produtos

    # --- MONTAR PLAYLIST ORDENADA (Vídeos e Propagandas) ---
    lista_mista = []

    # 1. Adiciona Produtos com Vídeo
    for p in dados_produtos:
        if p['template_video']:
            item = p.copy()
            item['tipo'] = 'produto'
            # Pega a ordem do objeto original (precisamos buscar no queryset ou passar no serializer)
            # O jeito mais limpo é adicionar 'ordem' no serializer, mas vamos fazer um map rápido:
            # (Simplificação: O serializer já deve mandar a ordem se atualizarmos ele, 
            #  mas vamos assumir que o 'p' tem os campos do serializer)
            
            # Se 'ordem' não estiver no serializer, precisamos adicionar no painel/serializers.py
            # Vamos assumir que adicionamos (veja nota abaixo) ou usar 0 default.
            item['ordem_visual'] = p.get('ordem', 0) 
            
            # Injeta a duração definida no template
            if 'template_video' in item and item['template_video']:
                item['duracao'] = item['template_video'].get('duracao', 15)
                
            lista_mista.append(item)

    # 2. Adiciona Propagandas
    propagandas = dispositivo.exibir_propagandas.filter(ativo=True)
    for prop in propagandas:
        lista_mista.append({
            "tipo": "propaganda",
            "url": prop.arquivo_video.url,
            "descricao": prop.descricao,
            "duracao": prop.duracao,
            "ordem_visual": prop.ordem
        })

    # 3. Ordena a lista final pelo campo 'ordem_visual'
    # Sort é estável, então itens com mesma ordem ficam na sequência de inserção
    lista_mista.sort(key=lambda x: x['ordem_visual'])

    response_data["playlist_final"] = lista_mista

    return Response(response_data)