import logging
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import Dispositivo, Produto, FamiliaProduto, Midia
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

    # Constrói a playlist com as entidades puras (Famílias e Mídias)
    playlist_final = _construir_playlist(dispositivo.playlist, request)

    response_data = {
        "config": {
            **DispositivoConfigSerializer(dispositivo).data,
            # Força o modo playlist pois é a arquitetura unificada
            "modo_exibicao": 'PLAYLIST' 
        },
        "produtos": dados_produtos,
        "playlist_final": playlist_final
    }

    return Response(response_data)


def _construir_playlist(playlist_config, request=None):
    """
    Processa a lista de itens configurados no admin (JSON) e hidrata
    com os dados reais do banco (Famílias e Mídias limpas).
    """
    if not playlist_config:
        return []

    playlist_processada = []
    
    for item in playlist_config:
        tipo = item.get('type')
        item_id = item.get('id')
        tempo_custom = item.get('tempo')

        # 1. TABELA DE PREÇOS
        if tipo == 'tabela_familia':
            try:
                familia = FamiliaProduto.objects.get(id=item_id)
                playlist_processada.append({
                    'tipo': 'tabela',
                    'familia_id': familia.id,
                    'descricao': f"Tabela: {familia.nome}",
                    'tempo_pagina': tempo_custom or 15
                })
            except FamiliaProduto.DoesNotExist:
                continue
                
        # 2. MÍDIA PURA (VÍDEO/IMAGEM)
        elif tipo == 'midia':
            try:
                midia = Midia.objects.get(id=item_id)
                url_arquivo = request.build_absolute_uri(midia.arquivo.url) if (midia.arquivo and request) else (midia.arquivo.url if midia.arquivo else '')

                playlist_processada.append({
                    'tipo': 'propaganda', # O JS entende 'propaganda' como Mídia em tela cheia
                    'url': url_arquivo,
                    'duracao': tempo_custom or midia.duracao,
                    'descricao': midia.nome,
                    'tipo_midia': midia.tipo # 'VIDEO' ou 'IMAGEM'
                })

            except Midia.DoesNotExist:
                continue

    return playlist_processada