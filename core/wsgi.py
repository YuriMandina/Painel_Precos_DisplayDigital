# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
from django.core.wsgi import get_wsgi_application


# ==============================================================================
#                                WSGI RUNTIME
# ==============================================================================
"""
Ponto de entrada para servidores web síncronos em produção (Gunicorn, uWSGI, etc).
"""
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()