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


class AutoplayPermissionsMiddleware:
    """
    Middleware que injeta headers de permissão de autoplay nas respostas HTTP.

    Por que isso é necessário?
    --------------------------
    Browsers modernos (Chrome 66+, Firefox 74+) e proxies de nuvem (Render, Cloudflare)
    podem enviar headers `Permissions-Policy: autoplay=()` que bloqueiam COMPLETAMENTE
    o autoplay de vídeo — mesmo com `muted` e `autoplay` definidos no elemento HTML.

    Smart TVs com SamsungBrowser (Tizen) são especialmente sensíveis a isso.

    Este middleware garante que o header correto seja enviado para:
    - /tv/          — A página da SPA da TV
    - /api/painel/  — As respostas da API (para o player saber que pode rodar)

    Headers injetados:
    - Permissions-Policy: autoplay=*          → Libera autoplay para qualquer origem
    - Cross-Origin-Embedder-Policy: unsafe-none → Evita bloqueio por isolamento de origem
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # Aplica apenas às rotas relevantes da TV e da API
        if request.path.startswith('/tv') or request.path.startswith('/api/painel'):
            response['Permissions-Policy'] = 'autoplay=*, fullscreen=*'
            response['Cross-Origin-Embedder-Policy'] = 'unsafe-none'
            response['Cross-Origin-Opener-Policy'] = 'unsafe-none'

        return response