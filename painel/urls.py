# ==============================================================================
#                                  IMPORTS
# ==============================================================================
from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.conf import settings
from urllib.parse import urlparse

from . import views, views_api, views_admin
from .forms import EmailLoginForm

# Extrai protocolo e domínio do SITE_URL para injetar nos e-mails
_site = urlparse(settings.SITE_URL)
_site_protocol = _site.scheme          # 'http' ou 'https'
_site_domain = _site.netloc            # 'displaydigital.onrender.com' ou 'localhost:8000'

# ==============================================================================
#                                 URL PATTERNS
# ==============================================================================

urlpatterns = [
    
    # --- REDIRECIONAMENTO RAIZ ---
    path('', RedirectView.as_view(url='/login/'), name='root_redirect'),

    # --- AUTENTICAÇÃO E SESSÃO ---
    path('login/', auth_views.LoginView.as_view(
        template_name='painel/login.html', 
        authentication_form=EmailLoginForm,
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', views.logout_customizado_view, name='logout'),
    
    # --- RECUPERAÇÃO DE SENHA ---
    path('recuperar-senha/', auth_views.PasswordResetView.as_view(
        template_name='painel/password_reset_form.html',
        email_template_name='painel/emails/password_reset_email.txt',
        html_email_template_name='painel/password_reset_email.html',
        subject_template_name='painel/password_reset_subject.txt',
        success_url='/recuperar-senha/enviado/',
        # Sobrescreve domain e protocol com os valores do SITE_URL
        # para que o link no e-mail aponte para o domínio correto em produção.
        extra_email_context={
            'protocol': _site_protocol,
            'domain': _site_domain,
        },
    ), name='password_reset'),
    
    path('recuperar-senha/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='painel/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('recuperar-senha/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='painel/password_reset_confirm.html',
        success_url='/recuperar-senha/concluido/'
    ), name='password_reset_confirm'),
    
    path('recuperar-senha/concluido/', auth_views.PasswordResetCompleteView.as_view(
        template_name='painel/password_reset_complete.html'
    ), name='password_reset_complete'),

    # --- AUTENTICAÇÃO ---
    # Segurança (django-axes)
    path('auth/bloqueado/', views.bloqueado_view, name='bloqueado'),
    path('auth/desbloquear-ip/<str:token>/', views.unlock_ip_view, name='unlock_ip'),

    # LGPD / Legal
    path('termos-de-uso/', views.TermosView.as_view(), name='termos'),
    path('politica-de-privacidade/', views.PrivacidadeView.as_view(), name='privacidade'),

    path('registro/', views.registro_view, name='registro'),
    path('verificar-email/<uuid:token>/', views.verificar_email_view, name='verificar_email'),
    path('aguardando-verificacao/', views.aguardando_verificacao_view, name='aguardando_verificacao'),
    path('reenviar-verificacao/', views.reenviar_verificacao_view, name='reenviar_verificacao'),

    # --- API ENDPOINTS (Client-side / TV) ---
    path('api/painel/parear/', views_api.parear_dispositivo, name='api_parear'),
    path('api/painel/<uuid:device_uuid>/', views_api.dados_painel, name='api_dados_painel'),
    path('api/debug/midias/<uuid:device_uuid>/', views_api.debug_midias, name='api_debug_midias'),

    # --- FRONTEND (SPA TV) ---
    path('tv/', views.tv_display_view, name='tv_display'),

    # --- DASHBOARD (Visão Geral) ---
    path('dashboard/', views_admin.dashboard_index, name='dashboard'),

    # --- MÓDULO: PRODUTOS ---
    path('dashboard/produtos/', views_admin.ProdutoListView.as_view(), name='produtos_list'),
    path('dashboard/produtos/novo/', views_admin.ProdutoCreateView.as_view(), name='produto_create'),
    path('dashboard/produtos/importar/', views_admin.ProdutoImportView.as_view(), name='produto_importar'),
    path('dashboard/produtos/<int:pk>/editar/', views_admin.ProdutoUpdateView.as_view(), name='produto_edit'),
    path('dashboard/produtos/<int:pk>/excluir/', views_admin.ProdutoDeleteView.as_view(), name='produto_delete'),
    path('dashboard/produtos/<int:pk>/toggle-visibilidade/', views_admin.produto_toggle_visibilidade, name='produto_toggle_visibilidade'),

    # --- MÓDULO: INTEGRAÇÃO OMIE ---
    path('dashboard/omie/sincronizar/', views_admin.omie_sincronizar_view, name='omie_sincronizar'),
    path('dashboard/omie/validacao/<int:sync_id>/', views_admin.omie_validacao_view, name='omie_validacao'),
    path('dashboard/omie/efetivar/<int:sync_id>/', views_admin.omie_efetivar_view, name='omie_efetivar'),
    path('dashboard/omie/denylist/', views_admin.DenyListListView.as_view(), name='omie_denylist'),
    path('dashboard/omie/denylist/<int:pk>/excluir/', views_admin.DenyListDeleteView.as_view(), name='omie_denylist_delete'),


    # --- MÓDULO: FAMÍLIAS DE PRODUTOS ---
    path('dashboard/familias/', views_admin.FamiliaListView.as_view(), name='familia_list'),
    path('dashboard/familias/nova/', views_admin.FamiliaCreateView.as_view(), name='familia_create'),
    path('dashboard/familias/<int:pk>/editar/', views_admin.FamiliaUpdateView.as_view(), name='familia_edit'),
    path('dashboard/familias/<int:pk>/excluir/', views_admin.FamiliaDeleteView.as_view(), name='familia_delete'),
    path('dashboard/familias/<int:pk>/produtos/json/', views_admin.familia_produtos_json, name='familia_produtos_json'),

    # --- MÓDULO: LISTAS PERSONALIZADAS ---
    path('dashboard/listas/', views_admin.ListaPersonalizadaListView.as_view(), name='lista_personalizada_list'),
    path('dashboard/listas/nova/', views_admin.ListaPersonalizadaCreateView.as_view(), name='lista_personalizada_create'),
    path('dashboard/listas/<int:pk>/editar/', views_admin.ListaPersonalizadaUpdateView.as_view(), name='lista_personalizada_edit'),
    path('dashboard/listas/<int:pk>/excluir/', views_admin.ListaPersonalizadaDeleteView.as_view(), name='lista_personalizada_delete'),
    path('dashboard/listas/<int:pk>/update-items/', views_admin.lista_personalizada_update_items, name='lista_personalizada_update_items'),

    # --- MÓDULO: DISPOSITIVOS (TVs) ---
    path('dashboard/dispositivos/', views_admin.DispositivoListView.as_view(), name='dispositivo_list'),
    path('dashboard/dispositivos/nova/', views_admin.DispositivoCreateView.as_view(), name='dispositivo_create'),
    path('dashboard/dispositivos/<int:pk>/editar/', views_admin.DispositivoUpdateView.as_view(), name='dispositivo_edit'),
    path('dashboard/dispositivos/<int:pk>/excluir/', views_admin.DispositivoDeleteView.as_view(), name='dispositivo_delete'),
    path('dashboard/dispositivos/<int:pk>/desconectar/', views_admin.DispositivoDesconectarView.as_view(), name='dispositivo_disconnect'),

    # --- MÓDULO: MÍDIAS (Biblioteca) ---
    path('dashboard/midias/', views_admin.MidiaListView.as_view(), name='midia_list'),
    path('dashboard/midias/nova/', views_admin.MidiaCreateView.as_view(), name='midia_create'),
    path('dashboard/midias/<int:pk>/excluir/', views_admin.MidiaDeleteView.as_view(), name='midia_delete'),

    # --- MÓDULO: CONFIGURAÇÕES ---
    path('dashboard/configuracoes/integracoes/', views_admin.ConfiguracaoIntegracoesView.as_view(), name='configuracao_integracoes'),

    # --- MÓDULO: ADMINISTRAÇÃO DE EQUIPE ---
    path('dashboard/equipe/', views_admin.EquipeListView.as_view(), name='equipe_list'),
    path('dashboard/equipe/convidar/', views_admin.EquipeConvidarView.as_view(), name='equipe_convidar'),
    path('dashboard/equipe/<int:pk>/toggle/', views_admin.equipe_toggle_status_view, name='equipe_toggle_status'),
    
    # --- CONVITES (Público) ---
    path('convite/<uuid:token>/', views.aceitar_convite_view, name='aceitar_convite'),
]