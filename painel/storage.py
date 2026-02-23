# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
from cloudinary_storage.storage import MediaCloudinaryStorage

# ==============================================================================
#                             STORAGE CUSTOMIZADO
# ==============================================================================
class MidiaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Storage inteligente que aceita imagens e vídeos nativamente no mesmo FileField,
    identificando corretamente o tipo de recurso para a API do Cloudinary.
    """
    
    def _get_resource_type(self, name: str) -> str:
        """
        Analisa a extensão do arquivo durante o upload e na geração da URL
        para classificar como 'video' ou 'image'.
        """
        if not name:
            return 'image'
            
        extensao = os.path.splitext(name)[1].lower()
        
        # Extensões clássicas de vídeo e animação pesada
        if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv']:
            return 'video'
        
        # Fallback padrão (JPG, PNG, GIF, WEBP, etc)
        return 'image'