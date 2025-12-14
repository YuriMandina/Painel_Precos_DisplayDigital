from django.shortcuts import render

def tv_display_view(request):
    """
    Renderiza o HTML vazio da TV. 
    Toda a inteligência virá via Javascript (API).
    """
    return render(request, 'painel/tv_display.html')