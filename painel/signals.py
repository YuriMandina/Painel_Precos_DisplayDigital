from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.core import signing
from axes.signals import user_locked_out
import logging

logger = logging.getLogger(__name__)

@receiver(user_locked_out)
def send_lockout_alert(sender, request, username, ip_address, **kwargs):
    """
    Envia um e-mail ao usuário quando a conta/IP for bloqueada
    por múltiplas tentativas falhas.
    """
    from django.contrib.auth.models import User
    
    from django.db.models import Q
    
    try:
        # Tenta achar por email ou username, já que no login via email o 'username' pode ser o email
        user = User.objects.get(Q(username=username) | Q(email=username))
    except User.DoesNotExist:
        # Se for um usuário inexistente tentando brute force,
        # não temos para quem enviar o alerta.
        return

    # Gera um token criptografado para liberar o IP
    # Válido por 1 hora
    token = signing.dumps({
        'username': username,
        'ip_address': ip_address
    })
    
    # Cria os links dinamicamente
    from django.urls import reverse
    base_unlock_url = request.build_absolute_uri(reverse('unlock_ip', kwargs={'token': token}))
    unlock_url = base_unlock_url
    reset_url = f"{base_unlock_url}?action=reset"

    context = {
        'nome': user.first_name or user.username,
        'ip_address': ip_address,
        'unlock_url': unlock_url,
        'reset_url': reset_url,
    }

    subject = "⚠️ Alerta de Segurança: Acesso Bloqueado no DisplayDigital"
    html_content = render_to_string('painel/emails/alerta_bloqueio.html', context)
    
    msg = EmailMultiAlternatives(
        subject=subject,
        body="Seu acesso foi bloqueado devido a múltiplas tentativas. Verifique seu e-mail formatado.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    msg.attach_alternative(html_content, "text/html")
    try:
        msg.send(fail_silently=False)
        logger.info(f"E-mail de bloqueio enviado para {user.email}")
    except Exception as e:
        logger.error(f"Erro ao enviar alerta de bloqueio: {str(e)}")
