# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
from django.core.asgi import get_asgi_application


# ==============================================================================
#                                ASGI RUNTIME
# ==============================================================================
"""
Ponto de entrada para servidores web assíncronos e suporte a WebSockets (Uvicorn, Daphne).
"""
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_asgi_application()