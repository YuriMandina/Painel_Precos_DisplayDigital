import logging
from rest_framework.decorators import api_view, permission_classes, authentication_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
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
@throttle_classes([AnonRateThrottle])
def parear_dispositivo(request):
    """
    Endpoint para conectar uma TV física ao sistema usando um código curto.
    """
    codigo = request.data.get('codigo', '').strip().upper()
    
    if not codigo:
        return Response({"erro": "Código não fornecido"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        dispositivo = Dispositivo.objects.get(codigo_acesso=codigo)
        logger.info(f"Dispositivo pareado com sucesso: {dispositivo.nome} (Empresa: {dispositivo.empresa.nome})")
        
        return Response({"uuid": dispositivo.uuid, "nome": dispositivo.nome})
    except Dispositivo.DoesNotExist:
        logger.warning(f"Tentativa de pareamento falhou. Código inválido: {codigo}")
        return Response({"erro": "Código inválido"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def dados_painel(request, device_uuid):
    """
    Retorna a configuração e o catálogo EXCLUSIVO da empresa deste dispositivo.
    """
    dispositivo = get_object_or_404(Dispositivo, uuid=device_uuid)
    empresa_do_dispositivo = dispositivo.empresa
    
    produtos_ativos = Produto.objects.filter(exibir_no_painel=True, empresa=empresa_do_dispositivo)
    produto_serializer = ProdutoSerializer(produtos_ativos, many=True, context={'request': request})

    playlist_final = _construir_playlist(dispositivo.playlist, empresa_do_dispositivo, request)

    response_data = {
        "config": {
            **DispositivoConfigSerializer(dispositivo).data,
            "modo_exibicao": 'PLAYLIST' 
        },
        "produtos": produto_serializer.data,
        "playlist_final": playlist_final
    }

    return Response(response_data)


def _construir_playlist(playlist_config, empresa, request=None):
    if not playlist_config:
        return []

    playlist_processada = []
    
    for item in playlist_config:
        tipo = item.get('type')
        item_id = item.get('id')
        
        # Garante que o tempo seja um número seguro
        try:
            tempo_custom = int(item.get('tempo', 15))
        except (TypeError, ValueError):
            tempo_custom = 15

        if tipo == 'tabela_familia':
            try:
                familia = FamiliaProduto.objects.get(id=item_id, empresa=empresa)
                playlist_processada.append({
                    'tipo': 'tabela',
                    'familia_id': familia.id,
                    'descricao': f"Tabela: {familia.nome}",
                    # REGRA: Usa o tempo configurado pelo usuário na playlist
                    'tempo_pagina': tempo_custom 
                })
            except FamiliaProduto.DoesNotExist:
                continue
                
        elif tipo == 'midia':
            try:
                midia = Midia.objects.get(id=item_id, empresa=empresa)
                url_arquivo = request.build_absolute_uri(midia.arquivo.url) if (midia.arquivo and request) else (midia.arquivo.url if midia.arquivo else '')

                playlist_processada.append({
                    'tipo': 'propaganda',
                    'url': url_arquivo,
                    # REGRA: Ignora a playlist e usa estritamente o tempo nativo da mídia do banco
                    'duracao': midia.duracao, 
                    'descricao': midia.nome,
                    'tipo_midia': midia.tipo
                })
            except Midia.DoesNotExist:
                continue

    return playlist_processada