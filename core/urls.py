"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    # Mude 'admin/' para algo obscuro, como 'acesso-root-sistema/' ou 'django-backend/'
    path('acesso-root-sistema/', admin.site.urls), 
    path('', include('painel.urls')),
]

# Configuração para servir arquivos de mídia em modo DEBUG (Local)
# IMPORTANTE: Usamos nossa própria view de streaming (media_stream_view) em vez do
# helper static() do Django porque o servidor de desenvolvimento não suporta
# HTTP Range Requests nativamente. Smart TVs exigem Range Requests para reproduzir
# vídeos — sem isso, gera "broken pipe" e o vídeo nunca toca na TV.
if settings.DEBUG:
    from painel.views import media_stream_view
    from django.urls import re_path
    
    urlpatterns += [
        # Endpoint de streaming com suporte a Range Requests (necessário para TVs)
        re_path(
            r'^media/(?P<file_path>.+)$',
            media_stream_view,
            name='media_stream'
        ),
    ]