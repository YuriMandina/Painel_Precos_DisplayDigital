import pandas as pd
from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.html import format_html
from django.core.exceptions import ValidationError

from .models import (
    FamiliaProduto, 
    Produto, 
    VideoTemplate, 
    Dispositivo, 
    VideoPropaganda
)
from .forms import ImportarProdutosForm

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    """
    Administração de Produtos com funcionalidade de Importação via Excel.
    """
    # Configuração da Listagem
    list_display = ('ordem', 'codigo', 'descricao', 'get_preco_formatado', 'em_oferta', 'exibir_no_painel')
    list_display_links = ('codigo', 'descricao')
    list_editable = ('ordem', 'em_oferta', 'exibir_no_painel')
    list_filter = ('familia', 'em_oferta', 'exibir_no_painel')
    search_fields = ('codigo', 'descricao')
    ordering = ('ordem', 'descricao')

    # Constantes das Colunas do Excel
    COL_CODIGO = 'CÓDIGO DO PRODUTO'
    COL_DESCRICAO = 'DESCRIÇÃO DO PRODUTO'
    COL_PRECO = 'PREÇO UNITÁRIO DE VENDA'
    COL_FAMILIA = 'FAMÍLIA DE PRODUTO'

    def get_preco_formatado(self, obj):
        return f"R$ {obj.preco}".replace('.', ',')
    get_preco_formatado.short_description = 'Preço'

    # --- Custom Views (Importação Excel) ---

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'importar-excel/', 
                self.admin_site.admin_view(self.importar_excel_view), 
                name='importar_produtos_excel'
            ),
        ]
        return custom_urls + urls

    def importar_excel_view(self, request):
        if request.method == "POST":
            form = ImportarProdutosForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    arquivo = request.FILES['arquivo_excel']
                    criados, atualizados = self.processar_arquivo(arquivo)
                    self.message_user(
                        request, 
                        f"Sucesso! {criados} produtos criados e {atualizados} atualizados.", 
                        level=messages.SUCCESS
                    )
                    return redirect('..')
                except Exception as e:
                    self.message_user(
                        request, 
                        f"Erro ao processar arquivo: {str(e)}", 
                        level=messages.ERROR
                    )
        else:
            form = ImportarProdutosForm()

        context = {
            'form': form,
            'opts': self.model._meta,
            'title': 'Importar Produtos via Excel'
        }
        return render(request, 'admin/importar_excel.html', context)

    @staticmethod
    def _limpar_valor_monetario(valor):
        """Converte string de moeda (R$ 1.000,00) para float (1000.00)."""
        if pd.isna(valor):
            return None
        
        if isinstance(valor, str):
            # Remove R$, espaços e pontos de milhar, troca vírgula por ponto
            limpo = valor.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.').strip()
            try:
                return float(limpo)
            except ValueError:
                return None
        return float(valor)

    def processar_arquivo(self, arquivo):
        """Lê o Excel e atualiza/cria produtos."""
        df = pd.read_excel(arquivo)
        
        # Normaliza colunas para uppercase e strip
        df.columns = [str(c).strip().upper() for c in df.columns]

        colunas_necessarias = [
            self.COL_CODIGO, 
            self.COL_DESCRICAO, 
            self.COL_PRECO, 
            self.COL_FAMILIA
        ]
        
        # Validação de Colunas
        for col in colunas_necessarias:
            if col not in df.columns:
                raise ValueError(
                    f"Coluna obrigatória '{col}' não encontrada. "
                    f"Colunas detectadas: {', '.join(df.columns)}"
                )

        count_criados = 0
        count_atualizados = 0

        for _, row in df.iterrows():
            # Extração de dados
            codigo = str(row[self.COL_CODIGO]).strip()
            descricao = str(row[self.COL_DESCRICAO]).strip()
            familia_nome = str(row[self.COL_FAMILIA]).strip().upper()
            preco = self._limpar_valor_monetario(row[self.COL_PRECO])

            if preco is None:
                continue

            # Lógica de Banco de Dados
            familia_obj, _ = FamiliaProduto.objects.get_or_create(nome=familia_nome)

            _, created = Produto.objects.update_or_create(
                codigo=codigo,
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
    list_display = ('nome',)
    search_fields = ('nome',)


@admin.register(VideoTemplate)
class VideoTemplateAdmin(admin.ModelAdmin):
    list_display = ('nome', 'duracao', 'botao_editor')
    
    def botao_editor(self, obj):
        url = reverse('editor_visual', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" style="background-color:#E91E63; color:white; '
            'padding:5px 10px; border-radius:5px; text-decoration:none;">'
            '🎨 Abrir Editor Visual</a>',
            url
        )
    botao_editor.short_description = 'Editor Visual'


@admin.register(VideoPropaganda)
class VideoPropagandaAdmin(admin.ModelAdmin):
    list_display = ('ordem', 'descricao', 'duracao', 'ativo')
    list_display_links = ('descricao',)
    list_editable = ('ordem', 'ativo')
    list_filter = ('ativo',)


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo_acesso', 'uuid', 'modo_exibicao', 'orientacao')
    readonly_fields = ('uuid', 'codigo_acesso')
    
    # Organização visual dos campos no formulário de edição
    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'titulo_exibicao', 'uuid', 'codigo_acesso')
        }),
        ('Configuração Técnica', {
            'fields': ('modo_exibicao', 'orientacao')
        }),
        ('Conteúdo', {
            'fields': ('playlist', 'exibir_apenas_familias', 'exibir_propagandas'),
            'description': 'Configure o que será exibido neste dispositivo.'
        }),
    )
    
    filter_horizontal = ('exibir_apenas_familias', 'exibir_propagandas')