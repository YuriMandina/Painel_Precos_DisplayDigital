from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

class EmailBackend(ModelBackend):
    """
    Autentica utilizando e-mail em vez do username padrão.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # O Django envia o email digitado no formulário através do parâmetro 'username'
        email = username or kwargs.get('email')
        if not email:
            return None
            
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
            
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
