from django.apps import AppConfig


class PainelConfig(AppConfig):
    """
    Configuração principal do aplicativo 'painel'.
    Define os comportamentos padrões do Django para este módulo.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'painel'
    verbose_name = 'Painel de Controle'