# ==============================================================================
#                                  IMPORTS
# ==============================================================================
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect, render
from .forms import RegistroForm
from .models import Empresa, Perfil
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import logout
from django.shortcuts import redirect


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


# ==============================================================================
#                                 BACKEND VIEWS
# ==============================================================================

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.contrib.auth import login
from .forms import RegistroForm, AceiteConviteForm
from .models import Empresa, Perfil, Convite

def registro_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            import uuid
            # Gera um username único usando UUID para satisfazer o modelo User do Django
            username = uuid.uuid4().hex[:30]
            email = form.cleaned_data['email']
            senha = form.cleaned_data['senha']
            nome = form.cleaned_data['nome']
            nome_empresa = form.cleaned_data['nome_empresa']

            # Cria a conta respeitando a arquitetura do Django
            user = User.objects.create_user(
                username=username, 
                email=email, 
                password=senha, 
                first_name=nome
            )

            # Nova empresa. Usuário vira o Master/Admin.
            empresa_nome = nome_empresa.strip()
            nova_empresa = Empresa.objects.create(nome=empresa_nome)
            Perfil.objects.create(
                usuario=user, empresa=nova_empresa, 
                is_admin=True, status=Perfil.Status.APROVADO
            )
            messages.success(request, 'Conta e Empresa criadas com sucesso! Você é o administrador.')

            return redirect('login')
    else:
        form = RegistroForm()
        
    return render(request, 'painel/registro.html', {'form': form})

def aceitar_convite_view(request: HttpRequest, token: str) -> HttpResponse:
    convite = get_object_or_404(Convite, token=token)
    
    if convite.status == Convite.Status.ACEITO:
        messages.error(request, 'Este convite já foi utilizado.')
        return redirect('login')

    if request.method == 'POST':
        form = AceiteConviteForm(request.POST)
        if form.is_valid():
            import uuid
            username = uuid.uuid4().hex[:30]
            senha = form.cleaned_data['senha']
            nome = form.cleaned_data['nome']
            
            user = User.objects.create_user(
                username=username, 
                email=convite.email, 
                password=senha, 
                first_name=nome
            )

            Perfil.objects.create(
                usuario=user, 
                empresa=convite.empresa, 
                is_admin=False, 
                status=Perfil.Status.APROVADO
            )
            
            convite.status = Convite.Status.ACEITO
            convite.save()
            
            messages.success(request, f'Você entrou na empresa {convite.empresa.nome}! Faça login.')
            return redirect('login')
    else:
        form = AceiteConviteForm(initial={'email': convite.email})
        
    return render(request, 'painel/convite_aceite.html', {'form': form, 'convite': convite})

def logout_customizado_view(request: HttpRequest) -> HttpResponse:
    """
    Substitui a view padrão do Django 5 para permitir que o sistema
    deslogue usuários via redirecionamento (GET) sem gerar erro 405.
    """
    logout(request)
    return redirect('login')