import json
import logging
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction

from .models import Midia, Layer

logger = logging.getLogger(__name__)

@csrf_exempt
@login_required
@transaction.atomic
def salvar_estudio(request, midia_id):
    """
    Salva o layout convertendo o JSON do front-end em registros reais
    na tabela Layer do banco de dados.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método não permitido"}, status=405)

    midia = get_object_or_404(Midia, pk=midia_id)

    try:
        # 1. Ler dados do Front
        payload = json.loads(request.body)
        
        # O front pode mandar dentro de 'elementos' ou 'camadas', normalizamos aqui:
        camadas_data = payload.get('camadas') or payload.get('elementos') or []
        
        # 2. Limpeza: Identificar quais camadas ainda existem
        # IDs que são números inteiros já existem no banco.
        ids_mantidos = [
            int(c['id']) for c in camadas_data 
            if str(c['id']).isdigit()
        ]
        
        # Remove do banco as camadas desta mídia que NÃO vieram no JSON (foram deletadas no editor)
        midia.layers.exclude(id__in=ids_mantidos).delete()

        # 3. Mapeamento de IDs Temporários (Front) -> IDs Reais (Banco)
        # Necessário para vincular filhos aos grupos recém-criados
        mapa_ids_temporarios = {}

        # 4. Estratégia de Salvamento: Primeiro Grupos, depois Filhos
        # Separamos para garantir que o Pai exista antes do Filho tentar se vincular
        grupos = [c for c in camadas_data if c['tipo'] == 'GROUP']
        itens_normais = [c for c in camadas_data if c['tipo'] != 'GROUP']

        # Função interna para salvar/atualizar uma camada
        def persistir_camada(dados, parent_obj=None):
            layer_id_raw = dados.get('id')
            is_new = not str(layer_id_raw).isdigit()
            
            # Monta os dados para o Model Layer
            campos = {
                'midia': midia,
                'tipo': dados.get('tipo', 'TEXT'),
                'config': dados.get('config', {}),
                'z_index': dados.get('z_index', 0),
                'is_locked': dados.get('is_locked', False),
                'parent': parent_obj
            }

            if is_new:
                # Cria nova
                nova_layer = Layer.objects.create(**campos)
                # Guarda no mapa se for grupo ou tiver ID temporário
                mapa_ids_temporarios[str(layer_id_raw)] = nova_layer
                return nova_layer
            else:
                # Atualiza existente
                Layer.objects.filter(id=int(layer_id_raw)).update(**campos)
                layer_atual = Layer.objects.get(id=int(layer_id_raw))
                mapa_ids_temporarios[str(layer_id_raw)] = layer_atual
                return layer_atual

        # Passo A: Salvar Grupos (que podem ser pais)
        for g_data in grupos:
            # Assumimos que grupos não têm pais (apenas 1 nível de aninhamento por enquanto)
            persistir_camada(g_data, parent_obj=None)

        # Passo B: Salvar Itens (que podem ter pais)
        for item_data in itens_normais:
            parent_id_raw = item_data.get('parent_id')
            parent_obj = None

            if parent_id_raw:
                parent_str = str(parent_id_raw)
                # Tenta achar no mapa (criado agora) ou no banco (se já existia)
                if parent_str in mapa_ids_temporarios:
                    parent_obj = mapa_ids_temporarios[parent_str]
                elif parent_str.isdigit():
                    # Caso raro de drag-and-drop entre grupos existentes
                    try:
                        parent_obj = Layer.objects.get(id=int(parent_str))
                    except Layer.DoesNotExist:
                        pass
            
            persistir_camada(item_data, parent_obj=parent_obj)

        return JsonResponse({"status": "success", "message": "Layout salvo com sucesso!"})

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "JSON inválido"}, status=400)
    except Exception as e:
        logger.error(f"Erro ao salvar layout {midia_id}: {str(e)}")
        return JsonResponse({"status": "error", "message": f"Erro interno: {str(e)}"}, status=500)