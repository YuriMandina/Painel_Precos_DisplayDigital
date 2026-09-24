# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import logging
from typing import List, Dict, Any, Optional

from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.decorators import (
    api_view, 
    permission_classes, 
    authentication_classes, 
    throttle_classes
)
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import Dispositivo, Produto, FamiliaProduto, Midia, ListaPersonalizada
from .serializers import ProdutoSerializer, DispositivoConfigSerializer


# ==============================================================================
#                               LOGGING SETUP
# ==============================================================================
logger = logging.getLogger(__name__)


# ==============================================================================
#                                API VIEWS
# ==============================================================================

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def parear_dispositivo(request: Request) -> Response:
    """
    Endpoint de registro inicial para dispositivos.
    Valida um código de acesso recebido via POST e retorna as credenciais (UUID) 
    do dispositivo correspondente caso exista.
    """
    codigo = request.data.get('codigo', '').strip().upper()
    
    if not codigo:
        return Response(
            {"erro": "Código de acesso não fornecido."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        dispositivo = Dispositivo.objects.get(codigo_acesso=codigo)
        logger.info(f"Dispositivo pareado com sucesso: {dispositivo.nome} (UUID: {dispositivo.uuid})")
        
        return Response({
            "uuid": str(dispositivo.uuid), 
            "nome": dispositivo.nome
        }, status=status.HTTP_200_OK)
        
    except Dispositivo.DoesNotExist:
        logger.warning(f"Tentativa de pareamento falhou. Código inválido: {codigo}")
        return Response(
            {"erro": "Código de acesso inválido ou dispositivo não encontrado."}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def dados_painel(request: Request, device_uuid: str) -> Response:
    """
    Fornece a carga de dados completa para a renderização do painel no dispositivo.
    Inclui as configurações do dispositivo, a lista global de produtos da empresa 
    e a estrutura processada da playlist.
    """
    dispositivo = get_object_or_404(Dispositivo, uuid=device_uuid)
    empresa_do_dispositivo = dispositivo.empresa
    
    # Recupera o catálogo completo de produtos da empresa. 
    # A filtragem de exibição ocorre no client-side com base nas regras de cada página.
    todos_produtos = Produto.objects.filter(empresa=empresa_do_dispositivo)
    produto_serializer = ProdutoSerializer(todos_produtos, many=True, context={'request': request})

    playlist_final = _construir_playlist(dispositivo.playlist, empresa_do_dispositivo, request)

    response_data = {
        "config": {
            **DispositivoConfigSerializer(dispositivo).data,
            "modo_exibicao": 'PLAYLIST' 
        },
        "produtos": produto_serializer.data,
        "playlist_final": playlist_final
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def debug_midias(request: Request, device_uuid: str) -> Response:
    """
    Endpoint de diagnóstico: inspeciona as URLs reais geradas para as mídias do dispositivo.
    """
    dispositivo = get_object_or_404(Dispositivo, uuid=device_uuid)
    empresa = dispositivo.empresa

    midias = Midia.objects.filter(empresa=empresa, ativo=True)
    resultado = []

    for m in midias:
        raw_url = m.arquivo.url if m.arquivo else ''

        resultado.append({
            'id': m.id,
            'nome': m.nome,
            'tipo': m.tipo,
            'duracao': m.duracao,
            'arquivo_name': m.arquivo.name if m.arquivo else '',
            'url_raw': raw_url,
            'url_final': request.build_absolute_uri(raw_url) if request and raw_url else raw_url,
        })

    return Response({
        'empresa': empresa.nome,
        'total_midias': len(resultado),
        'midias': resultado,
    }, status=status.HTTP_200_OK)


# ==============================================================================
#                            HELPER FUNCTIONS
# ==============================================================================

def _construir_playlist(playlist_config: Any, empresa: Any, request: Request = None) -> Any:
    """
    Processa o dicionário de configuração da playlist bruto armazenado no banco,
    resolvendo referências de banco de dados (Tabelas e Mídias) e gerando um 
    array padronizado pronto para consumo pelo front-end da TV.
    Suporta playlists simples (List) e layouts asimétricos (Dict).
    """
    if not playlist_config:
        return []

    # Helper function to process a list of items
    def process_items(items):
        processed = []
        if not items: return processed
        
        for item in items:
            tipo = item.get('type')
            item_id = item.get('id')
            
            hidden_products = item.get('hidden_products', [])
            forced_products = item.get('forced_products', [])
            
            try:
                tempo_custom = int(item.get('tempo', 15))
            except (TypeError, ValueError):
                tempo_custom = 15

            if tipo == 'tabela_familia':
                try:
                    familia = FamiliaProduto.objects.get(id=item_id, empresa=empresa)
                    processed.append({
                        'tipo': 'tabela',
                        'familia_id': familia.id,
                        'descricao': f"Tabela: {familia.nome}",
                        'tempo_pagina': tempo_custom,
                        'hidden_products': hidden_products,
                        'forced_products': forced_products 
                    })
                except FamiliaProduto.DoesNotExist:
                    continue

            elif tipo == 'lista_personalizada':
                try:
                    lista = ListaPersonalizada.objects.get(id=item_id, empresa=empresa)
                    produtos_ids = list(lista.itens.order_by('ordem').values_list('produto_id', flat=True))
                    processed.append({
                        'tipo': 'tabela',
                        'descricao': lista.nome,
                        'tempo_pagina': tempo_custom,
                        'produtos_ordenados': produtos_ids
                    })
                except ListaPersonalizada.DoesNotExist:
                    continue
                    
            elif tipo == 'midia':
                try:
                    midia = Midia.objects.get(id=item_id, empresa=empresa)
                    
                    url_arquivo = ''
                    if midia.arquivo:
                        raw_url = midia.arquivo.url
                        if request:
                            url_arquivo = request.build_absolute_uri(raw_url)
                        else:
                            url_arquivo = raw_url

                    processed.append({
                        'tipo': 'propaganda',
                        'url': url_arquivo,
                        'duracao': midia.duracao, 
                        'descricao': midia.nome,
                        'tipo_midia': midia.tipo
                    })
                except Midia.DoesNotExist:
                    continue
        return processed

    if isinstance(playlist_config, dict) and playlist_config.get('layout') == 'split_asimetrico':
        return {
            'layout': 'split_asimetrico',
            'zones': {
                'left': process_items(playlist_config.get('zones', {}).get('left', [])),
                'right': process_items(playlist_config.get('zones', {}).get('right', []))
            }
        }
    elif isinstance(playlist_config, list):
        return process_items(playlist_config)
    else:
        return []