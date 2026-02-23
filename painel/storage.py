# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
import cloudinary.uploader
from cloudinary_storage.storage import MediaCloudinaryStorage


# ==============================================================================
#                             STORAGE CUSTOMIZADO
# ==============================================================================
class MidiaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Storage inteligente que permite o upload misto (Imagens e Vídeos) 
    nativamente no mesmo campo (FileField) integrado ao Cloudinary.
    """
    
    RESOURCE_TYPE = 'auto'
    
    def url(self, name: str) -> str:
        """
        Corrige o link de entrega/reprodução da mídia.
        O pacote base sempre gera as URLs apontando para o diretório '/image/'.
        Interceptamos a string e substituímos para '/video/' caso seja um arquivo de mídia.
        """
        url_gerada = super().url(name)
        
        if not name:
            return url_gerada
            
        extensao = os.path.splitext(name)[1].lower()
        
        if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv']:
            # Força o roteamento correto para o player de vídeo do Cloudinary
            return url_gerada.replace('/image/upload/', '/video/upload/', 1)
            
        return url_gerada

    def delete(self, name: str) -> None:
        """Garante a exclusão física do arquivo no Cloudinary."""
        if not name:
            return
            
        extensao = os.path.splitext(name)[1].lower()
        res_type = 'video' if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv'] else 'image'
        public_id = self._get_public_id(name)
        
        try:
            cloudinary.uploader.destroy(
                public_id, 
                invalidate=True, 
                resource_type=res_type
            )
        except Exception:
            pass