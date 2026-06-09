# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
import mimetypes

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse, Http404
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.decorators.http import require_GET

from .forms import RegistroForm
from .models import Empresa, Perfil


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


@require_GET
def media_stream_view(request: HttpRequest, file_path: str) -> HttpResponse:
    """
    Endpoint de streaming de mídia com suporte completo a HTTP Range Requests.

    Por que isso é necessário?
    --------------------------
    Smart TVs (WebOS, Tizen, Android TV) exigem Range Requests para reprodução
    de vídeo. O servidor de desenvolvimento do Django NÃO suporta Range Requests
    nativamente — ele retorna o arquivo inteiro (200 OK) ignorando o header
    `Range`, o que causa "broken pipe" e falha silenciosa de reprodução nas TVs.
    
    Em produção (Render + Cloudinary), as URLs são absolutas e o Cloudinary
    suporta Range Requests nativamente, então esta view NÃO é necessária lá.
    Esta view é registrada APENAS quando DEBUG=True.
    
    Como funciona:
    -------------
    1. Valida o caminho do arquivo para prevenir path traversal (segurança).
    2. Detecta o MIME type automaticamente para o header Content-Type.
    3. Lê o header `Range` do request (ex: `bytes=0-1023`).
    4. Retorna 206 Partial Content com os headers corretos se Range estiver presente.
    5. Retorna 200 OK com o arquivo completo se não houver Range header.
    """
    # Resolve o caminho absoluto e valida que está dentro de MEDIA_ROOT (anti path-traversal)
    safe_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, file_path))
    media_root = os.path.normpath(str(settings.MEDIA_ROOT))

    if not safe_path.startswith(media_root):
        raise Http404("Acesso negado.")

    if not os.path.isfile(safe_path):
        raise Http404("Arquivo de mídia não encontrado.")

    # Detecta o MIME type pelo nome do arquivo
    content_type, _ = mimetypes.guess_type(safe_path)
    if not content_type:
        content_type = 'application/octet-stream'

    file_size = os.path.getsize(safe_path)
    chunk_size = 8 * 1024 * 1024  # 8 MB por chunk

    range_header = request.META.get('HTTP_RANGE', '').strip()

    if range_header and range_header.startswith('bytes='):
        # --- RESPOSTA PARTIAL CONTENT (206) ---
        try:
            ranges = range_header[6:]  # remove 'bytes='
            start_str, end_str = ranges.split('-')
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
        except (ValueError, AttributeError):
            # Range header malformado: retorna arquivo completo
            start, end = 0, file_size - 1

        # Garante limites válidos
        start = max(0, start)
        end = min(end, file_size - 1)
        length = end - start + 1

        def file_iterator(path, offset, length, chunk):
            with open(path, 'rb') as f:
                f.seek(offset)
                remaining = length
                while remaining > 0:
                    read_size = min(chunk, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        response = StreamingHttpResponse(
            file_iterator(safe_path, start, length, chunk_size),
            status=206,
            content_type=content_type,
        )
        response['Content-Length'] = str(length)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'

    else:
        # --- RESPOSTA COMPLETA (200) ---
        def full_file_iterator(path, chunk):
            with open(path, 'rb') as f:
                while True:
                    data = f.read(chunk)
                    if not data:
                        break
                    yield data

        response = StreamingHttpResponse(
            full_file_iterator(safe_path, chunk_size),
            status=200,
            content_type=content_type,
        )
        response['Content-Length'] = str(file_size)
        response['Accept-Ranges'] = 'bytes'

    # Headers de cache para a TV não ter de re-baixar o vídeo a cada exibição
    response['Cache-Control'] = 'public, max-age=3600'

    return response


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