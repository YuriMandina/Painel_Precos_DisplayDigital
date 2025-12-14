from rest_framework.decorators import api_view, permission_classes, authentication_classes # <--- IMPORTANTE: Adicione authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Dispositivo, Produto
from .serializers import ProdutoSerializer, DispositivoConfigSerializer

# --- ROTA BLINDADA CONTRA ERRO CSRF ---
@csrf_exempt
@api_view(['POST'])
@authentication_classes([]) # <--- A SOLUÇÃO: Isso diz "Não use sessão/cookies aqui", o que desativa a checagem CSRF do DRF
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

@api_view(['GET'])
@permission_classes([AllowAny]) # Também liberamos a leitura dos dados para a TV
def dados_painel(request, device_uuid):
    dispositivo = get_object_or_404(Dispositivo, uuid=device_uuid)
    
    # Lógica do Título
    familias_alvo = dispositivo.exibir_apenas_familias.all()
    titulo_exibicao = "OFERTAS ESPECIAIS"
    
    if familias_alvo.count() == 1:
        titulo_exibicao = familias_alvo.first().nome.upper()
    elif dispositivo.nome:
        titulo_exibicao = dispositivo.nome.upper()

    response_data = {
        "config": {
            **DispositivoConfigSerializer(dispositivo).data,
            "titulo_exibicao": titulo_exibicao
        },
        "produtos": [],
        "ofertas_destaque": []
    }

    # Query e Filtros
    query_produtos = Produto.objects.filter(exibir_no_painel=True)
    if familias_alvo.exists():
        query_produtos = query_produtos.filter(familia__in=familias_alvo)
    
    query_produtos = query_produtos.order_by('familia__nome', 'descricao')
    
    # Serialização
    serializer = ProdutoSerializer(query_produtos, many=True, context={'request': request})
    dados_produtos = serializer.data
    
    response_data["produtos"] = dados_produtos
    response_data["ofertas_destaque"] = [p for p in dados_produtos if p['template_video'] is not None]

    return Response(response_data)