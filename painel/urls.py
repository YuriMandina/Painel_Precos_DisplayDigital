from django.urls import path
from . import views_api, views, views_editor, views_admin

# Boas práticas: Namespace para evitar colisão de nomes de rotas
# app_name = 'painel' 

urlpatterns = [
    # ==========================================
    # API ENDPOINTS (Consumidos pela TV/JS)
    # ==========================================
    path('api/painel/parear/', views_api.parear_dispositivo, name='api_parear'),
    path('api/painel/<uuid:device_uuid>/', views_api.dados_painel, name='api_dados_painel'),
    path('api/editor/salvar/<int:template_id>/', views_editor.salvar_layout, name='api_salvar_layout'),

    # ==========================================
    # FRONTEND (TV Display)
    # ==========================================
    path('tv/', views.tv_display_view, name='tv_display'),

    # ==========================================
    # EDITOR VISUAL
    # ==========================================
    path('editor/<int:template_id>/', views_editor.editor_visual, name='editor_visual'),

    # ==========================================
    # DASHBOARD ADMINISTRATIVO
    # ==========================================
    path('dashboard/', views_admin.dashboard_index, name='dashboard'),

    # --- Produtos ---
    path('dashboard/produtos/', views_admin.ProdutoListView.as_view(), name='produtos_list'),
    path('dashboard/produtos/novo/', views_admin.ProdutoCreateView.as_view(), name='produto_create'),
    path('dashboard/produtos/importar/', views_admin.ProdutoImportView.as_view(), name='produto_importar'),
    path('dashboard/produtos/<int:pk>/editar/', views_admin.ProdutoUpdateView.as_view(), name='produto_edit'),
    path('dashboard/produtos/<int:pk>/excluir/', views_admin.ProdutoDeleteView.as_view(), name='produto_delete'),

    # --- Famílias ---
    path('dashboard/familias/', views_admin.FamiliaListView.as_view(), name='familia_list'),
    path('dashboard/familias/nova/', views_admin.FamiliaCreateView.as_view(), name='familia_create'),
    path('dashboard/familias/<int:pk>/editar/', views_admin.FamiliaUpdateView.as_view(), name='familia_edit'),
    path('dashboard/familias/<int:pk>/excluir/', views_admin.FamiliaDeleteView.as_view(), name='familia_delete'),

    # --- Templates de Vídeo ---
    path('dashboard/templates/', views_admin.TemplateListView.as_view(), name='template_list'),
    path('dashboard/templates/novo/', views_admin.TemplateCreateView.as_view(), name='template_create'),
    path('dashboard/templates/<int:pk>/editar/', views_admin.TemplateUpdateView.as_view(), name='template_edit'),
    path('dashboard/templates/<int:pk>/excluir/', views_admin.TemplateDeleteView.as_view(), name='template_delete'),

    # --- Dispositivos (TVs) ---
    path('dashboard/dispositivos/', views_admin.DispositivoListView.as_view(), name='dispositivo_list'),
    path('dashboard/dispositivos/nova/', views_admin.DispositivoCreateView.as_view(), name='dispositivo_create'),
    path('dashboard/dispositivos/<int:pk>/editar/', views_admin.DispositivoUpdateView.as_view(), name='dispositivo_edit'),
    path('dashboard/dispositivos/<int:pk>/excluir/', views_admin.DispositivoDeleteView.as_view(), name='dispositivo_delete'),
]