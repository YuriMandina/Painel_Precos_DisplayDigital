import pandas as pd
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.html import format_html
from .models import FamiliaProduto, Produto, VideoTemplate, Dispositivo
from .forms import ImportarProdutosForm

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descricao', 'preco_formatado', 'familia', 'em_oferta', 'exibir_no_painel')
    list_filter = ('familia', 'em_oferta', 'exibir_no_painel')
    search_fields = ('codigo', 'descricao')
    list_editable = ('em_oferta', 'exibir_no_painel')
    
    # Exibe o R$ bonitinho na lista
    def preco_formatado(self, obj):
        return f"R$ {obj.preco}".replace('.', ',')
    preco_formatado.short_description = 'Preço'

    # --- Lógica do Botão de Importação ---
    
    def get_urls(self):
        # Adiciona nossa URL personalizada antes das URLs padrões do admin
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
                    return redirect('..') # Volta para a lista de produtos
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
        # Lê o Excel usando Pandas
        df = pd.read_excel(arquivo)
        
        # Normaliza nomes das colunas (remove espaços extras e converte para maiúsculas)
        df.columns = [c.strip().upper() for c in df.columns]

        colunas_esperadas = ['CÓDIGO DO PRODUTO', 'DESCRIÇÃO DO PRODUTO', 'VALOR DO PRODUTO', 'FAMÍLIA']
        
        # Verifica se as colunas existem
        for col in colunas_esperadas:
            if col not in df.columns:
                raise ValueError(f"A coluna '{col}' não foi encontrada no Excel.")

        produtos_atualizados = 0
        produtos_criados = 0

        for index, row in df.iterrows():
            codigo = str(row['CÓDIGO DO PRODUTO']).strip()
            descricao = str(row['DESCRIÇÃO DO PRODUTO']).strip()
            familia_nome = str(row['FAMÍLIA']).strip().upper()
            
            # Tratamento de Preço (R$ 1.200,50 -> 1200.50)
            valor_raw = row['VALOR DO PRODUTO']
            if isinstance(valor_raw, str):
                valor_raw = valor_raw.replace('R$', '').replace('.', '').replace(',', '.').strip()
            
            try:
                preco = float(valor_raw)
            except ValueError:
                continue # Pula se o preço for inválido

            # 1. Garante que a Família existe
            familia_obj, _ = FamiliaProduto.objects.get_or_create(nome=familia_nome)

            # 2. Cria ou Atualiza o Produto
            # update_or_create tenta buscar pelo código. Se achar, atualiza os defaults. Se não, cria.
            obj, created = Produto.objects.update_or_create(
                codigo=codigo,
                defaults={
                    'descricao': descricao,
                    'preco': preco,
                    'familia': familia_obj
                }
            )
            
            if created:
                produtos_criados += 1
            else:
                produtos_atualizados += 1
                
        return True

# --- Registros Simples dos Outros Models ---

@admin.register(FamiliaProduto)
class FamiliaProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome',)

@admin.register(VideoTemplate)
class VideoTemplateAdmin(admin.ModelAdmin):
    list_display = ('nome', 'arquivo_video')

@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'uuid', 'modo_exibicao')
    readonly_fields = ('uuid',)