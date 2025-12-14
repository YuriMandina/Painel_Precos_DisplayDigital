from django.contrib import admin
from .models import FamiliaProduto, Produto, VideoTemplate, Dispositivo

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descricao', 'preco', 'familia', 'em_oferta', 'exibir_no_painel')
    list_filter = ('familia', 'em_oferta', 'exibir_no_painel')
    search_fields = ('codigo', 'descricao')
    list_editable = ('preco', 'em_oferta', 'exibir_no_painel') # Edição rápida na lista

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