# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
import logging
import cloudinary.uploader
from cloudinary_storage.storage import MediaCloudinaryStorage

logger = logging.getLogger(__name__)


# ==============================================================================
#                             STORAGE CUSTOMIZADO
# ==============================================================================
class MidiaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Storage inteligente que permite o upload misto (Imagens e Vídeos) 
    nativamente no mesmo campo (FileField) integrado ao Cloudinary.
    """
    
    # Devolvemos a inteligência nativa para a biblioteca.
    RESOURCE_TYPE = 'auto'
    
    def url(self, name: str) -> str:
        """Corrige o link de entrega/reprodução da mídia para a TV e Prévia."""
        url_gerada = super().url(name)
        
        if not name:
            return url_gerada
            
        extensao = os.path.splitext(name)[1].lower()
        
        if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv']:
            return url_gerada.replace('/image/upload/', '/video/upload/', 1)
            
        return url_gerada

    def delete(self, name: str) -> None:
        """Garante a exclusão física do arquivo no Cloudinary de forma resiliente."""
        if not name:
            return
            
        extensao = os.path.splitext(name)[1].lower()
        res_type = 'video' if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv'] else 'image'
        
        public_id = os.path.splitext(name)[0]
        
        try:
            cloudinary.uploader.destroy(
                public_id, 
                invalidate=True, 
                resource_type=res_type
            )
        except Exception as e:
            logger.error(f"Falha ao deletar asset no Cloudinary (ID: {public_id}): {e}")

        # Garante que o Django execute sua rotina de limpeza isolando possíveis erros.
        try:
            super().delete(name)
        except Exception:
            pass