from django.urls import path
from . import views_api
from . import views # <--- Importe as views normais

urlpatterns = [
    path('api/painel/parear/', views_api.parear_dispositivo, name='api_parear'), # <--- Nova rota
    path('api/painel/<uuid:device_uuid>/', views_api.dados_painel, name='api_dados_painel'),
    path('tv/', views.tv_display_view, name='tv_display'),
]