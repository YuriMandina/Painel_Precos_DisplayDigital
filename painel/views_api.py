import logging
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import Dispositivo, Produto, VideoPropaganda, FamiliaProduto
from .serializers import ProdutoSerializer, DispositivoConfigSerializer

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def parear_dispositivo(request):
    """
    Endpoint para conectar uma TV física ao sistema usando um código curto.
    """
    codigo = request.data.get('codigo', '').strip().upper()
    
    if not codigo:
        return Response(
            {"erro": "Código não fornecido"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        dispositivo = Dispositivo.objects.get(codigo_acesso=codigo)
        logger.info(f"Dispositivo pareado com sucesso: {dispositivo.nome}")
        
        return Response({
            "uuid": dispositivo.uuid, 
            "nome": dispositivo.nome
        })
    except Dispositivo.DoesNotExist:
        logger.warning(f"Tentativa de pareamento falhou. Código inválido: {codigo}")
        return Response(
            {"erro": "Código inválido"}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def dados_painel(request, device_uuid):
    """
    Retorna toda a configuração necessária para a TV rodar:
    1. Configurações do Dispositivo
    2. Lista de Produtos (Catálogo)
    3. Playlist Sequencial (O que tocar e em qual ordem)
    """
    dispositivo = get_object_or_404(Dispositivo, uuid=device_uuid)
    
    # Carrega catálogo completo de produtos ativos
    produtos_ativos = Produto.objects.filter(exibir_no_painel=True)
    produto_serializer = ProdutoSerializer(
        produtos_ativos, 
        many=True, 
        context={'request': request}
    )
    dados_produtos = produto_serializer.data

    # Constrói a playlist baseada na configuração manual (Drag & Drop)
    playlist_final = _construir_playlist(dispositivo.playlist, dados_produtos)

    response_data = {
        "config": {
            **DispositivoConfigSerializer(dispositivo).data,
            # Força o modo playlist pois é a nova arquitetura unificada
            "modo_exibicao": 'PLAYLIST' 
        },
        "produtos": dados_produtos,
        "playlist_final": playlist_final
    }

    return Response(response_data)


def _construir_playlist(playlist_config, catalogo_produtos):
    """
    Processa a lista de itens configurados no admin (JSON) e hidrata
    com os dados reais do banco (Famílias, Vídeos, Produtos).
    """
    if not playlist_config:
        return []

    playlist_processada = []
    
    # Otimização: Cria mapa de produtos {id: dados} para busca rápida O(1)
    mapa_produtos = {
        str(p.get('id')): p for p in catalogo_produtos
    }
    # Mapa alternativo por código, caso o JSON use código
    mapa_produtos_codigo = {
        str(p.get('codigo')): p for p in catalogo_produtos
    }

    for item in playlist_config:
        tipo = item.get('type')
        item_id = item.get('id')
        tempo_custom = item.get('tempo', 15)

        if tipo == 'tabela_familia':
            # Recupera Família
            try:
                familia = FamiliaProduto.objects.get(id=item_id)
                playlist_processada.append({
                    'tipo': 'tabela',
                    'familia_id': familia.id,
                    'descricao': familia.nome,
                    'tempo_pagina': tempo_custom
                })
            except FamiliaProduto.DoesNotExist:
                continue

        elif tipo == 'propaganda':
            # Recupera Vídeo Institucional
            try:
                propaganda = VideoPropaganda.objects.get(id=item_id, ativo=True)
                playlist_processada.append({
                    "tipo": "propaganda",
                    "url": propaganda.arquivo_video.url,
                    "descricao": propaganda.descricao,
                    "duracao": propaganda.duracao
                })
            except VideoPropaganda.DoesNotExist:
                continue

        elif tipo == 'produto_video':
            # Recupera Produto com Template de Vídeo
            prod_data = mapa_produtos.get(str(item_id)) or mapa_produtos_codigo.get(str(item_id))

            if prod_data and prod_data.get('template_video'):
                novo_item = prod_data.copy()
                novo_item['tipo'] = 'produto_video'
                # Usa a duração definida no template do vídeo
                novo_item['duracao'] = novo_item['template_video'].get('duracao', 15)
                playlist_processada.append(novo_item)

    return playlist_processada