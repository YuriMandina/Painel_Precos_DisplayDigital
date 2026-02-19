from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist

class TenantMiddleware:
    """
    Verifica se o usuário logado possui um Perfil (e consequentemente uma Empresa) 
    vinculado a ele antes de acessar qualquer página do dashboard.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Só aplica a verificação para URLs que começam com '/dashboard/' 
        # (ignora tela de login, /acesso-root-sistema/ e API da TV)
        if request.path.startswith('/dashboard/') and request.user.is_authenticated:
            try:
                # Tenta acessar o perfil para forçar o erro caso não exista
                _ = request.user.perfil.empresa
            except ObjectDoesNotExist:
                # Se for superuser, redireciona pro admin pra ele se arrumar
                if request.user.is_superuser:
                    messages.error(request, "Superusuário: Você precisa vincular seu usuário a uma Empresa (Criar Perfil) antes de acessar o Dashboard.")
                    return redirect('/acesso-root-sistema/')
                
                # Se for usuário comum, desloga e avisa
                messages.error(request, "Seu usuário não está vinculado a nenhuma empresa. Contate o suporte.")
                return redirect('logout')

        response = self.get_response(request)
        return response