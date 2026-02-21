# ==============================================================================
#                                  IMPORTS
# ==============================================================================
from django.apps import AppConfig


# ==============================================================================
#                             CONFIGURAÇÃO DA APLICAÇÃO
# ==============================================================================

class PainelConfig(AppConfig):
    """Configuração de metadados e comportamentos padrão do módulo 'painel'."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'painel'
    verbose_name = 'Painel de Controle'