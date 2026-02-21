# ==============================================================================
#                                  IMPORTS
# ==============================================================================
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse


# ==============================================================================
#                                 FRONTEND VIEWS
# ==============================================================================

def tv_display_view(request: HttpRequest) -> HttpResponse:
    """
    Renderiza o template base da Single Page Application (SPA) para a TV.
    A hidratação do conteúdo (produtos, vídeos, playlist) é delegada ao 
    client-side via chamadas assíncronas (AJAX/Fetch) à API.
    """
    return render(request, 'painel/tv_display.html')