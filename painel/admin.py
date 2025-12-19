import pandas as pd
from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.html import format_html
from .models import FamiliaProduto, Produto, VideoTemplate, Dispositivo, VideoPropaganda
from .forms import ImportarProdutosForm

# --- ADMIN DE PRODUTOS (COM IMPORTAÇÃO EXCEL E ORDENAÇÃO) ---
@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    # 'ordem' é a primeira coluna, mas definimos 'codigo' e 'descricao' como links abaixo
    list_display = ('ordem', 'codigo', 'descricao', 'preco_formatado', 'em_oferta', 'exibir_no_painel')
    
    # CORREÇÃO DO ERRO E124: Definimos explicitamente quais campos são links
    list_display_links = ('codigo', 'descricao') 
    
    # Agora podemos editar 'ordem' direto na lista sem conflito
    list_editable = ('ordem', 'em_oferta', 'exibir_no_painel')
    
    list_filter = ('familia', 'em_oferta', 'exibir_no_painel')
    search_fields = ('codigo', 'descricao')
    
    def preco_formatado(self, obj):
        return f"R$ {obj.preco}".replace('.', ',')
    preco_formatado.short_description = 'Preço'

    # --- Lógica de Importação Excel (Mantida) ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('importar-excel/', self.admin_site.admin_view(self.importar_excel_view), name='importar_produtos_excel'),
        ]
        return custom_urls + urls

    def importar_excel_view(self, request):
        if request.method == "POST":
            form = ImportarProdutosForm(request.POST, request.FILES)
            if form.is_valid():
                arquivo = request.FILES['arquivo_excel']
                try:
                    self.processar_arquivo(arquivo)
                    self.message_user(request, "Importação concluída com sucesso!", level=messages.SUCCESS)
                    return redirect('..')
                except Exception as e:
                    self.message_user(request, f"Erro ao processar arquivo: {str(e)}", level=messages.ERROR)
        else:
            form = ImportarProdutosForm()

        context = {
            'form': form,
            'opts': self.model._meta,
            'title': 'Importar Produtos via Excel'
        }
        return render(request, 'admin/importar_excel.html', context)

    def processar_arquivo(self, arquivo):
        df = pd.read_excel(arquivo)
        df.columns = [str(c).strip().upper() for c in df.columns]

        col_codigo = 'CÓDIGO DO PRODUTO'
        col_descricao = 'DESCRIÇÃO DO PRODUTO'
        col_preco = 'PREÇO UNITÁRIO DE VENDA'
        col_familia = 'FAMÍLIA DE PRODUTO'
        
        colunas_esperadas = [col_codigo, col_descricao, col_preco, col_familia]
        
        for col in colunas_esperadas:
            if col not in df.columns:
                colunas_encontradas = ", ".join(df.columns)
                raise ValueError(f"A coluna '{col}' não foi encontrada. Colunas lidas: {colunas_encontradas}")

        produtos_atualizados = 0
        produtos_criados = 0

        for index, row in df.iterrows():
            codigo = str(row[col_codigo]).strip()
            descricao = str(row[col_descricao]).strip()
            familia_nome = str(row[col_familia]).strip().upper()
            
            valor_raw = row[col_preco]
            if pd.isna(valor_raw): continue

            if isinstance(valor_raw, str):
                valor_raw = valor_raw.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.').strip()
            
            try:
                preco = float(valor_raw)
            except ValueError:
                continue

            familia_obj, _ = FamiliaProduto.objects.get_or_create(nome=familia_nome)

            obj, created = Produto.objects.update_or_create(
                codigo=codigo,
                defaults={
                    'descricao': descricao,
                    'preco': preco,
                    'familia': familia_obj
                }
            )
            
            if created: produtos_criados += 1
            else: produtos_atualizados += 1
                
        return True

# --- ADMIN DE FAMÍLIAS ---
@admin.register(FamiliaProduto)
class FamiliaProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome',)

# --- ADMIN DE TEMPLATES ---
@admin.register(VideoTemplate)
class VideoTemplateAdmin(admin.ModelAdmin):
    list_display = ('nome', 'duracao', 'botao_editor')
    
    def botao_editor(self, obj):
        url = reverse('editor_visual', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" style="background-color:#E91E63; color:white; padding:5px 10px; border-radius:5px; text-decoration:none;">🎨 Abrir Editor Visual</a>',
            url
        )
    botao_editor.short_description = 'Editor'

# --- ADMIN DE PROPAGANDAS (Onde deu o erro) ---
@admin.register(VideoPropaganda)
class VideoPropagandaAdmin(admin.ModelAdmin):
    list_display = ('ordem', 'descricao', 'duracao', 'ativo')
    
    # CORREÇÃO: Definimos 'descricao' como o link para editar
    list_display_links = ('descricao',)
    
    list_editable = ('ordem', 'ativo')

# --- ADMIN DE DISPOSITIVOS ---
@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo_acesso', 'uuid', 'modo_exibicao', 'orientacao')
    readonly_fields = ('uuid', 'codigo_acesso')
    fields = ('nome', 'codigo_acesso', 'uuid', 'modo_exibicao', 'orientacao', 'exibir_apenas_familias', 'exibir_propagandas')
    filter_horizontal = ('exibir_apenas_familias', 'exibir_propagandas') # Facilita seleção de muitos itens