from django.shortcuts import render
from django.http import HttpRequest, HttpResponse

def tv_display_view(request: HttpRequest) -> HttpResponse:
    """
    Renderiza o HTML base da TV (Single Page Application).
    
    A lógica de conteúdo (produtos, vídeos, playlist) é carregada 
    assincronamente via JavaScript consumindo a API.
    """
    return render(request, 'painel/tv_display.html')