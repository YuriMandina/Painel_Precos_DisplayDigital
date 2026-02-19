from django.urls import path
from django.contrib.auth import views as auth_views
from . import views_api, views, views_admin

urlpatterns = [
    # ==========================================
    # AUTENTICAÇÃO (Login / Logout)
    # ==========================================
    path('login/', auth_views.LoginView.as_view(
        template_name='painel/login.html', 
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # ==========================================
    # API ENDPOINTS (Consumidos pela TV/JS)
    # ==========================================
    path('api/painel/parear/', views_api.parear_dispositivo, name='api_parear'),
    path('api/painel/<uuid:device_uuid>/', views_api.dados_painel, name='api_dados_painel'),

    # ==========================================
    # FRONTEND (TV Display)
    # ==========================================
    path('tv/', views.tv_display_view, name='tv_display'),

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

    # --- Dispositivos (TVs) ---
    path('dashboard/dispositivos/', views_admin.DispositivoListView.as_view(), name='dispositivo_list'),
    path('dashboard/dispositivos/nova/', views_admin.DispositivoCreateView.as_view(), name='dispositivo_create'),
    path('dashboard/dispositivos/<int:pk>/editar/', views_admin.DispositivoUpdateView.as_view(), name='dispositivo_edit'),
    path('dashboard/dispositivos/<int:pk>/excluir/', views_admin.DispositivoDeleteView.as_view(), name='dispositivo_delete'),
    path('dashboard/dispositivos/<int:pk>/desconectar/', views_admin.DispositivoDesconectarView.as_view(), name='dispositivo_disconnect'),

    # --- MÍDIAS (Biblioteca) ---
    path('dashboard/midias/', views_admin.MidiaListView.as_view(), name='midia_list'),
    path('dashboard/midias/nova/', views_admin.MidiaCreateView.as_view(), name='midia_create'),
    path('dashboard/midias/<int:pk>/editar/', views_admin.MidiaUpdateView.as_view(), name='midia_edit'),
    path('dashboard/midias/<int:pk>/excluir/', views_admin.MidiaDeleteView.as_view(), name='midia_delete'),
]