# ==============================================================================
#                                  IMPORTS
# ==============================================================================
from typing import Any, Tuple, Optional

import pandas as pd
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

from .forms import ImportarProdutosForm
from .models import (
    Dispositivo, 
    Empresa, 
    FamiliaProduto, 
    Midia, 
    Perfil, 
    Produto,
    TokenVerificacaoEmail
)


# ==============================================================================
#                           ADMIN: CONTROLE DE TENANTS (SAAS)
# ==============================================================================

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    """Gestão de instâncias de Inquilinos (Tenants) via root-admin."""
    list_display = ('nome', 'cnpj', 'ativo', 'created_at')
    search_fields = ('nome', 'cnpj')
    list_filter = ('ativo',)


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    """Gestão de vínculos de autorização (Usuário <-> Tenant)."""
    list_display = ('usuario', 'empresa')
    search_fields = ('usuario__username', 'usuario__email', 'empresa__nome')
    list_filter = ('empresa',)


# ==============================================================================
#                           ADMIN: DADOS DE NEGÓCIO E UI
# ==============================================================================

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    """
    Interface administrativa principal para manipulação de Produtos.
    Inclui override de rotas para processamento em lote via planilhas.
    """
    list_display = (
        'empresa', 'ordem', 'codigo', 'descricao', 
        'get_preco_formatado', 'em_oferta', 'exibir_no_painel'
    )
    list_display_links = ('codigo', 'descricao')
    list_editable = ('ordem', 'em_oferta', 'exibir_no_painel')
    list_filter = ('empresa', 'familia', 'em_oferta', 'exibir_no_painel')
    search_fields = ('codigo', 'descricao')
    ordering = ('empresa', 'ordem', 'descricao')

    # Constantes de mapeamento de colunas da planilha
    COL_CODIGO = 'CÓDIGO DO PRODUTO'
    COL_DESCRICAO = 'DESCRIÇÃO DO PRODUTO'
    COL_PRECO = 'PREÇO UNITÁRIO DE VENDA'
    COL_FAMILIA = 'FAMÍLIA DE PRODUTO'

    @admin.display(description='Preço')
    def get_preco_formatado(self, obj: Produto) -> str:
        """Formata a saída decimal monetária na listagem."""
        return f"R$ {obj.preco}".replace('.', ',')

    def get_urls(self) -> list:
        """Injeta a rota de endpoint customizada para upload de planilhas."""
        urls = super().get_urls()
        custom_urls = [
            path(
                'importar-excel/', 
                self.admin_site.admin_view(self.importar_excel_view), 
                name='importar_produtos_excel'
            ),
        ]
        return custom_urls + urls

    def importar_excel_view(self, request: HttpRequest) -> HttpResponse:
        """View administrativa customizada para renderização e processamento do formulário de importação."""
        if request.method == "POST":
            form = ImportarProdutosForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    arquivo = request.FILES['arquivo_excel']
                    empresa = request.user.perfil.empresa 
                    criados, atualizados = self.processar_arquivo(arquivo, empresa)
                    
                    self.message_user(
                        request, 
                        f"Processamento concluído: {criados} inserções, {atualizados} atualizações.", 
                        level=messages.SUCCESS
                    )
                    return redirect('..')
                except Exception as e:
                    self.message_user(
                        request, 
                        f"Falha na integração: {str(e)}", 
                        level=messages.ERROR
                    )
        else:
            form = ImportarProdutosForm()

        context = {
            'form': form,
            'opts': self.model._meta,
            'title': 'Importar Lote de Produtos (Excel)'
        }
        return render(request, 'admin/importar_excel.html', context)

    @staticmethod
    def _limpar_valor_monetario(valor: Any) -> Optional[float]:
        """Rotina de sanitização para conversão de strings monetárias sujas do Excel para Float."""
        if pd.isna(valor):
            return None
        if isinstance(valor, str):
            limpo = valor.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.').strip()
            try:
                return float(limpo)
            except ValueError:
                return None
        return float(valor)

    def processar_arquivo(self, arquivo: Any, empresa: Empresa) -> Tuple[int, int]:
        """
        Executa a leitura do dataframe, validação de colunas e operação de Upsert (Update or Create) 
        dos registros no banco de dados, retornando a volumetria de operações realizadas.
        """
        df = pd.read_excel(arquivo)
        df.columns = [str(c).strip().upper() for c in df.columns]

        colunas_necessarias = [self.COL_CODIGO, self.COL_DESCRICAO, self.COL_PRECO, self.COL_FAMILIA]
        
        for col in colunas_necessarias:
            if col not in df.columns:
                raise ValueError(f"Constraint violada: A coluna obrigatória '{col}' não foi detectada no arquivo.")

        count_criados = 0
        count_atualizados = 0

        for _, row in df.iterrows():
            codigo = str(row[self.COL_CODIGO]).strip()
            descricao = str(row[self.COL_DESCRICAO]).strip()
            familia_nome = str(row[self.COL_FAMILIA]).strip().upper()
            preco = self._limpar_valor_monetario(row[self.COL_PRECO])

            if preco is None:
                continue

            familia_obj, _ = FamiliaProduto.objects.get_or_create(nome=familia_nome, empresa=empresa)

            _, created = Produto.objects.update_or_create(
                codigo=codigo,
                empresa=empresa,
                defaults={
                    'descricao': descricao,
                    'preco': preco,
                    'familia': familia_obj
                }
            )

            if created:
                count_criados += 1
            else:
                count_atualizados += 1

        return count_criados, count_atualizados


@admin.register(FamiliaProduto)
class FamiliaProdutoAdmin(admin.ModelAdmin):
    """Gestão de agrupamentos (Categorias) de Produtos."""
    list_display = ('empresa', 'nome')
    search_fields = ('nome', 'empresa__nome')
    list_filter = ('empresa',)


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    """Gestão de configuração técnica e autorização de Endpoints (TVs)."""
    list_display = ('nome', 'empresa', 'codigo_acesso', 'uuid', 'modo_exibicao', 'orientacao')
    readonly_fields = ('uuid', 'codigo_acesso')
    list_filter = ('empresa', 'modo_exibicao', 'orientacao')
    search_fields = ('nome', 'empresa__nome')
    
    fieldsets = (
        ('Identificação e Pareamento', {
            'fields': ('empresa', 'nome', 'titulo_exibicao', 'uuid', 'codigo_acesso')
        }),
        ('Especificações de Hardware/Layout', {
            'fields': ('modo_exibicao', 'orientacao')
        }),
        ('Engine de Renderização', {
            'fields': ('playlist', 'exibir_apenas_familias'),
            'description': 'Estrutura de dados para o client-side player.'
        }),
    )
    
    filter_horizontal = ('exibir_apenas_familias',)


@admin.register(Midia)
class MidiaAdmin(admin.ModelAdmin):
    """Gestão do repositório de binários/assets visuais vinculados aos Tenants."""
    list_display = ('nome', 'empresa', 'tipo', 'duracao', 'ativo')
    list_filter = ('empresa', 'tipo', 'ativo')
    search_fields = ('nome', 'empresa__nome')
    readonly_fields = ('tipo',)


@admin.register(TokenVerificacaoEmail)
class TokenVerificacaoEmailAdmin(admin.ModelAdmin):
    """Monitora tokens de verificação de e-mail gerados no cadastro."""
    list_display = ('usuario', 'token', 'criado_em', 'usado')
    list_filter = ('usado',)
    search_fields = ('usuario__email',)
    readonly_fields = ('usuario', 'token', 'criado_em')