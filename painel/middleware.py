# ==============================================================================
#                                  IMPORTS
# ==============================================================================
from typing import Callable

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.contrib.auth import logout
from painel.models import Perfil


# ==============================================================================
#                                MIDDLEWARES
# ==============================================================================

class TenantMiddleware:
    """
    Middleware de validação de Tenant.
    Intercepta requisições direcionadas ao dashboard para assegurar que o usuário 
    autenticado possua um Perfil ativo e vinculado a uma Empresa (Tenant) válida.
    """
    
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Executa a validação de autorização de escopo por Tenant em rotas restritas.
        Redireciona usuários sem vínculo para o painel de administração (superusers) 
        ou encerra a sessão (usuários padrão).
        """
        if request.path.startswith('/dashboard/') and request.user.is_authenticated:
            try:
                perfil = request.user.perfil
                
                if perfil.status == Perfil.Status.PENDENTE:
                    messages.warning(
                        request, 
                        "Sua conta foi criada e está aguardando a aprovação do administrador da sua empresa."
                    )
                    return redirect('logout')
                
            except ObjectDoesNotExist:
                if request.user.is_superuser:
                    messages.error(request, "Superusuário: Vínculo de Tenant (Empresa) ausente.")
                    return redirect('/admin/')
                
                messages.error(request, "Acesso negado: Usuário sem vínculo.")
                return redirect('logout')

        return self.get_response(request)