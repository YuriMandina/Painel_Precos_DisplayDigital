import pandas as pd
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Empresa, Perfil, FamiliaProduto, Produto, Dispositivo, Midia
from .forms import ImportarProdutosForm


# --- ADMIN DE USUÁRIOS E EMPRESAS (SAAS) ---

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'ativo', 'created_at')
    search_fields = ('nome', 'cnpj')
    list_filter = ('ativo',)


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa')
    search_fields = ('usuario__username', 'usuario__email', 'empresa__nome')
    list_filter = ('empresa',)


# --- ADMIN DE DADOS DO SISTEMA ---

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    """
    Administração de Produtos com funcionalidade de Importação via Excel.
    """
    # Adicionada a 'empresa' na exibição e nos filtros para o SuperAdmin
    list_display = ('empresa', 'ordem', 'codigo', 'descricao', 'get_preco_formatado', 'em_oferta', 'exibir_no_painel')
    list_display_links = ('codigo', 'descricao')
    list_editable = ('ordem', 'em_oferta', 'exibir_no_painel')
    list_filter = ('empresa', 'familia', 'em_oferta', 'exibir_no_painel')
    search_fields = ('codigo', 'descricao')
    ordering = ('empresa', 'ordem', 'descricao')

    COL_CODIGO = 'CÓDIGO DO PRODUTO'
    COL_DESCRICAO = 'DESCRIÇÃO DO PRODUTO'
    COL_PRECO = 'PREÇO UNITÁRIO DE VENDA'
    COL_FAMILIA = 'FAMÍLIA DE PRODUTO'

    def get_preco_formatado(self, obj):
        return f"R$ {obj.preco}".replace('.', ',')
    get_preco_formatado.short_description = 'Preço'

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
                    # Passamos a empresa do superuser logado para a importação do admin
                    empresa = request.user.perfil.empresa 
                    criados, atualizados = self.processar_arquivo(arquivo, empresa)
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
        if pd.isna(valor):
            return None
        if isinstance(valor, str):
            limpo = valor.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.').strip()
            try:
                return float(limpo)
            except ValueError:
                return None
        return float(valor)

    def processar_arquivo(self, arquivo, empresa):
        df = pd.read_excel(arquivo)
        df.columns = [str(c).strip().upper() for c in df.columns]

        colunas_necessarias = [self.COL_CODIGO, self.COL_DESCRICAO, self.COL_PRECO, self.COL_FAMILIA]
        
        for col in colunas_necessarias:
            if col not in df.columns:
                raise ValueError(f"Coluna obrigatória '{col}' não encontrada.")

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
    list_display = ('empresa', 'nome')
    search_fields = ('nome', 'empresa__nome')
    list_filter = ('empresa',)


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'codigo_acesso', 'uuid', 'modo_exibicao', 'orientacao')
    readonly_fields = ('uuid', 'codigo_acesso')
    list_filter = ('empresa', 'modo_exibicao', 'orientacao')
    search_fields = ('nome', 'empresa__nome')
    
    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'nome', 'titulo_exibicao', 'uuid', 'codigo_acesso')
        }),
        ('Configuração Técnica', {
            'fields': ('modo_exibicao', 'orientacao')
        }),
        ('Conteúdo', {
            'fields': ('playlist', 'exibir_apenas_familias'),
            'description': 'Configure o que será exibido neste dispositivo.'
        }),
    )
    
    filter_horizontal = ('exibir_apenas_familias',)


@admin.register(Midia)
class MidiaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'tipo', 'duracao', 'ativo')
    list_filter = ('empresa', 'tipo', 'ativo')
    search_fields = ('nome', 'empresa__nome')
    readonly_fields = ('tipo',)