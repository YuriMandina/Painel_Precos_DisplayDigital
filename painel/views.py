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
from django.views.generic import TemplateView

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
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from .forms import RegistroForm, AceiteConviteForm
from .models import Empresa, Perfil, Convite, TokenVerificacaoEmail
import logging

logger = logging.getLogger(__name__)


def _enviar_email_verificacao(request, user, token_obj):
    """
    Dispara o e-mail de verificação de conta para o usuário recém-cadastrado.
    Usa settings.SITE_URL para garantir que o link aponte para o domínio correto
    (produção ou desenvolvimento), independente do host da requisição.
    """
    path = reverse('verificar_email', kwargs={'token': str(token_obj.token)})
    link = f"{settings.SITE_URL}{path}"

    assunto = 'Confirme seu e-mail — DisplayDigital'
    contexto = {
        'nome': user.first_name or user.email,
        'link': link,
    }

    # Corpo em texto puro (fallback)
    texto = (
        f"Olá, {contexto['nome']}!\n\n"
        "Obrigado por criar sua conta no DisplayDigital.\n\n"
        "Para ativar sua conta, acesse o link abaixo:\n"
        f"{link}\n\n"
        "Este link expira em 48 horas.\n\n"
        "Se você não criou esta conta, ignore este e-mail.\n\n"
        "Atenciosamente,\nEquipe DisplayDigital"
    )

    # Corpo HTML
    html = render_to_string('painel/emails/verificacao_conta.html', contexto, request=request)

    mensagem = EmailMultiAlternatives(
        subject=assunto,
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    mensagem.attach_alternative(html, 'text/html')
    mensagem.send(fail_silently=False)


def registro_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            import uuid
            username = uuid.uuid4().hex[:30]
            email = form.cleaned_data['email']
            senha = form.cleaned_data['senha']
            nome = form.cleaned_data['nome']
            nome_empresa = form.cleaned_data['nome_empresa']

            # Cria usuário INATIVO até confirmar o e-mail
            user = User.objects.create_user(
                username=username,
                email=email,
                password=senha,
                first_name=nome,
                is_active=False,  # Bloqueado até verificar o e-mail
            )

            nova_empresa = Empresa.objects.create(nome=nome_empresa.strip())
            Perfil.objects.create(
                usuario=user, empresa=nova_empresa,
                is_admin=True, status=Perfil.Status.APROVADO
            )

            # Gera o token de verificação
            token_obj = TokenVerificacaoEmail.objects.create(usuario=user)

            # Tenta enviar e-mail
            try:
                _enviar_email_verificacao(request, user, token_obj)
                messages.success(
                    request,
                    f'Conta criada! Enviamos um e-mail de confirmação para <strong>{email}</strong>. '
                    'Acesse-o para ativar sua conta.'
                )
            except Exception as e:
                logger.error(f"Falha ao enviar e-mail de verificação para {email}: {e}")
                # Ativa o usuário mesmo assim se o email falhar, para não bloquear o cadastro por problema de SMTP
                user.is_active = True
                user.save(update_fields=['is_active'])
                messages.warning(
                    request,
                    'Conta criada! Houve um problema ao enviar o e-mail de confirmação. '
                    'Sua conta foi ativada automaticamente. Faça login.'
                )
                return redirect('login')

            return redirect('aguardando_verificacao')
    else:
        form = RegistroForm()

    return render(request, 'painel/registro.html', {'form': form})


def aguardando_verificacao_view(request: HttpRequest) -> HttpResponse:
    """Tela informativa exibida após o cadastro, orientando o usuário a checar o e-mail."""
    return render(request, 'painel/aguardando_verificacao.html')


def verificar_email_view(request: HttpRequest, token: str) -> HttpResponse:
    """
    Processa o clique no link de verificação de e-mail.
    Ativa o usuário e invalida o token.
    """
    token_obj = get_object_or_404(TokenVerificacaoEmail, token=token)

    if token_obj.usado:
        messages.info(request, 'Este link de verificação já foi utilizado. Faça login normalmente.')
        return redirect('login')

    if token_obj.esta_expirado():
        messages.error(
            request,
            'Este link de verificação expirou (válido por 48h). '
            '<a href="/reenviar-verificacao/">Clique aqui para reenviar o e-mail</a>.'
        )
        return redirect('login')

    # Ativa o usuário e marca o token como usado
    user = token_obj.usuario
    user.is_active = True
    user.save(update_fields=['is_active'])

    token_obj.usado = True
    token_obj.save(update_fields=['usado'])

    messages.success(request, f'E-mail confirmado com sucesso! Bem-vindo(a), {user.first_name or user.email}!')
    return redirect('login')


def reenviar_verificacao_view(request: HttpRequest) -> HttpResponse:
    """
    Permite ao usuário solicitar o reenvio do e-mail de verificação.
    Útil quando o link expirou ou o e-mail sumiu.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            user = User.objects.get(email=email, is_active=False)
        except User.DoesNotExist:
            messages.error(request, 'Nenhuma conta pendente de verificação encontrada para este e-mail.')
            return render(request, 'painel/reenviar_verificacao.html')

        # Deleta token antigo e cria um novo
        TokenVerificacaoEmail.objects.filter(usuario=user).delete()
        token_obj = TokenVerificacaoEmail.objects.create(usuario=user)

        try:
            _enviar_email_verificacao(request, user, token_obj)
            messages.success(request, f'E-mail de verificação reenviado para {email}!')
        except Exception as e:
            logger.error(f"Falha ao reenviar verificação para {email}: {e}")
            messages.error(request, 'Falha ao enviar o e-mail. Tente novamente mais tarde.')

    return render(request, 'painel/reenviar_verificacao.html')



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


# ==============================================================================
#                          LGPD E TERMOS
# ==============================================================================

class TermosView(TemplateView):
    template_name = 'painel/legal/termos.html'

class PrivacidadeView(TemplateView):
    template_name = 'painel/legal/privacidade.html'

# ==============================================================================
#                          SEGURANÇA (AXES)
# ==============================================================================

def bloqueado_view(request):
    """
    View para onde o django-axes redireciona quando o limite é excedido.
    """
    return render(request, 'painel/auth/bloqueado.html')

def unlock_ip_view(request, token):
    from django.core import signing
    from axes.utils import reset
    
    try:
        # Válido por 1 hora
        data = signing.loads(token, max_age=3600)
        username = data['username']
        ip_address = data['ip_address']
    except signing.SignatureExpired:
        messages.error(request, "O link de desbloqueio expirou. Aguarde o tempo de bloqueio automático.")
        return redirect('login')
    except signing.BadSignature:
        messages.error(request, "Link de desbloqueio inválido.")
        return redirect('login')

    action = request.GET.get('action')
    
    if action == 'reset':
        # Se NÃO foi ele, NÃO desbloqueia o IP do atacante e redireciona para redefinir a senha
        messages.warning(request, "Por segurança, o IP suspeito continuará bloqueado. Redefina sua senha abaixo para proteger a sua conta.")
        return redirect('password_reset')

    # Se foi o usuário (action != 'reset'), desbloqueia o IP dele no axes
    reset(username=username, ip=ip_address)
    messages.success(request, "Seu IP foi liberado com sucesso. Você pode tentar fazer login novamente.")
        
    return redirect('login')