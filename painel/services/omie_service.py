import requests
from django.db import transaction
from decimal import Decimal, InvalidOperation

from ..models import Empresa, Produto, FamiliaProduto, ProdutoIgnoradoOmie, SincronizacaoOmie
import logging

logger = logging.getLogger(__name__)

class OmieService:
    BASE_URL = "https://app.omie.com.br/api/v1"

    def __init__(self, empresa: Empresa):
        self.empresa = empresa
        self.app_key = empresa.omie_app_key
        self.app_secret = empresa.omie_app_secret

    def _make_request(self, endpoint: str, call: str, param: dict) -> dict:
        url = f"{self.BASE_URL}{endpoint}"
        payload = {
            "call": call,
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "param": [param]
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def fetch_all_products(self) -> list:
        """Busca todos os produtos ativos do Omie paginando a API."""
        produtos_omie = []
        pagina = 1
        total_paginas = 1

        while pagina <= total_paginas:
            data = self._make_request(
                endpoint="/geral/produtos/",
                call="ListarProdutos",
                param={
                    "pagina": pagina,
                    "registros_por_pagina": 100,
                    "apenas_importado_api": "N",
                    "filtrar_apenas_omiepdv": "N"
                }
            )

            total_paginas = data.get("total_de_paginas", 1)
            items = data.get("produto_servico_cadastro", [])
            produtos_omie.extend(items)
            
            pagina += 1

        return produtos_omie
        
    def fetch_all_families(self) -> dict:
        """Busca as famílias para mapear codigo_familia -> nome da familia. Retorna um dict."""
        familias_map = {}
        pagina = 1
        total_paginas = 1
        
        # Fazemos um try/except pois o cliente pode não ter famílias ou a API pode não responder
        try:
            while pagina <= total_paginas:
                data = self._make_request(
                    endpoint="/geral/familias/",
                    call="PesquisarFamilias",
                    param={
                        "pagina": pagina,
                        "registros_por_pagina": 100
                    }
                )
                total_paginas = data.get("total_de_paginas", 1)
                items = data.get("famCadastro", [])
                
                for f in items:
                    codigo = str(f.get('codigo', ''))
                    descricao = f.get('nomeFamilia', 'Geral')
                    if codigo:
                        familias_map[codigo] = descricao
                
                pagina += 1
        except Exception as e:
            logger.warning(f"Erro ao buscar famílias Omie para a empresa {self.empresa.nome}: {e}")
            
        return familias_map

    def processar_sincronizacao_preview(self) -> SincronizacaoOmie:
        """
        Gera o estado de preview cruzando os dados do Omie com a base local.
        Retorna uma instância salva de SincronizacaoOmie com status PENDENTE.
        """
        if not self.app_key or not self.app_secret:
            raise ValueError("Credenciais do Omie não configuradas para esta empresa.")

        # 1. Buscar do Omie
        produtos_omie_brutos = self.fetch_all_products()
        familias_map = self.fetch_all_families()

        # 2. Buscar locais
        produtos_locais = {p.codigo: p for p in Produto.objects.filter(empresa=self.empresa)}
        ignorados = set(ProdutoIgnoradoOmie.objects.filter(empresa=self.empresa).values_list('codigo', flat=True))

        novos = []
        alterados = []
        inalterados_count = 0
        ignorados_count = 0

        # 3. Cruzar dados
        for po in produtos_omie_brutos:
            # Em Omie: 'codigo' é o SKU definido pelo usuário. 'codigo_produto' é o ID interno do Omie.
            # O cliente espera usar o 'codigo' (SKU).
            codigo_omie = po.get('codigo', '')
            if not codigo_omie:
                # Fallback caso o SKU esteja em branco, usamos o ID interno.
                codigo_omie = po.get('codigo_produto', '')
                
            codigo = str(codigo_omie).strip()
            
            if not codigo:
                continue

            if codigo in ignorados:
                ignorados_count += 1
                continue

            descricao = po.get('descricao', '').strip()
            
            # Formatar preço
            valor = po.get('valor_unitario', 0)
            try:
                preco_novo = Decimal(str(valor)).quantize(Decimal('0.01'))
            except (InvalidOperation, ValueError):
                preco_novo = Decimal('0.00')

            # Nome da família
            codigo_familia = str(po.get('codigo_familia', ''))
            familia_nome = familias_map.get(codigo_familia, 'Sem Categoria')
            
            # Não importar se o preço for zero (Regra de negócio usual)
            if preco_novo <= 0:
                continue

            payload = {
                'codigo': codigo,
                'descricao': descricao,
                'preco': float(preco_novo),
                'familia': familia_nome
            }

            if codigo in produtos_locais:
                prod_local = produtos_locais[codigo]
                preco_antigo = prod_local.preco.quantize(Decimal('0.01'))
                desc_antiga = prod_local.descricao
                familia_antiga = prod_local.familia.nome if prod_local.familia else 'Sem Categoria'

                mudou_preco = (preco_antigo != preco_novo)
                mudou_dados = (desc_antiga != descricao or familia_antiga != familia_nome)

                if mudou_preco or mudou_dados:
                    payload['preco_antigo'] = float(preco_antigo)
                    payload['mudou_preco'] = mudou_preco
                    payload['mudou_dados'] = mudou_dados
                    
                    if desc_antiga != descricao:
                        payload['nome_antigo'] = desc_antiga
                    
                    alterados.append(payload)
                else:
                    inalterados_count += 1
            else:
                novos.append(payload)

        # 4. Salvar Sync
        dados_sync = {
            'novos': novos,
            'alterados': alterados,
            'metricas': {
                'inalterados_count': inalterados_count,
                'ignorados_count': ignorados_count,
                'total_omie': len(produtos_omie_brutos)
            }
        }

        sync_obj = SincronizacaoOmie.objects.create(
            empresa=self.empresa,
            status=SincronizacaoOmie.Status.PENDENTE,
            dados=dados_sync
        )

        return sync_obj

    @transaction.atomic
    def efetivar_sincronizacao(self, sync_id: int, itens_selecionados: list, itens_denylist: list):
        """
        Recebe a lista de códigos (codigo) que o usuário aprovou para salvar,
        e os que ele marcou para denylist. Atualiza o banco de dados.
        """
        sync_obj = SincronizacaoOmie.objects.get(id=sync_id, empresa=self.empresa)
        
        if sync_obj.status != SincronizacaoOmie.Status.PENDENTE:
            raise ValueError("Esta sincronização não está pendente.")

        # Converter para set para busca rápida O(1)
        set_aprovados = set(itens_selecionados)
        set_denylist = set(itens_denylist)

        dados = sync_obj.dados
        todos_preview = dados.get('novos', []) + dados.get('alterados', [])

        count_criados = 0
        count_atualizados = 0

        # Processar Deny List
        for codigo in set_denylist:
            # Encontrar os detalhes no preview
            item_dados = next((item for item in todos_preview if item['codigo'] == codigo), None)
            defaults = {}
            if item_dados:
                defaults['descricao'] = item_dados.get('descricao', '')
                defaults['familia'] = item_dados.get('familia', '')
                
            ProdutoIgnoradoOmie.objects.update_or_create(
                empresa=self.empresa, 
                codigo=codigo,
                defaults=defaults
            )

        # Cache de famílias para evitar muitas queries
        familias_db = {f.nome: f for f in FamiliaProduto.objects.filter(empresa=self.empresa)}

        # Processar Aprovados
        for item in todos_preview:
            codigo = item['codigo']
            
            # Se não foi aprovado ou se foi pra denylist (mesmo que estivesse na lista de aprovados por erro), pula.
            if codigo not in set_aprovados or codigo in set_denylist:
                continue
                
            familia_nome = item['familia']
            
            # Garantir família
            if familia_nome not in familias_db:
                fam_obj = FamiliaProduto.objects.create(empresa=self.empresa, nome=familia_nome)
                familias_db[familia_nome] = fam_obj
                
            familia_obj = familias_db[familia_nome]

            # Upsert
            prod, created = Produto.objects.update_or_create(
                empresa=self.empresa,
                codigo=codigo,
                defaults={
                    'descricao': item['descricao'],
                    'preco': Decimal(str(item['preco'])),
                    'familia': familia_obj
                }
            )

            if created:
                count_criados += 1
            else:
                count_atualizados += 1

        sync_obj.status = SincronizacaoOmie.Status.CONCLUIDA
        sync_obj.save()

        return count_criados, count_atualizados
