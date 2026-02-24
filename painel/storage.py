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
            # Cobre os padrões gerados pela biblioteca (image ou raw) para forçar o player de vídeo do Cloudinary
            url_gerada = url_gerada.replace('/image/upload/', '/video/upload/', 1)
            url_gerada = url_gerada.replace('/raw/upload/', '/video/upload/', 1)
            
        return url_gerada

    def delete(self, name: str) -> None:
        """Garante a exclusão física do arquivo no Cloudinary de forma resiliente."""
        if not name:
            return
            
        extensao = os.path.splitext(name)[1].lower()
        res_type = 'video' if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv'] else 'image'
        
        base_name = os.path.splitext(name)[0]
        
        # Matriz de tentativas para cobrir como a biblioteca salvou o public_id internamente
        tentativas_exclusao = [
            (name, res_type),
            (base_name, res_type),
            (name, 'raw'),
            (base_name, 'raw')
        ]
        
        for pid, rtype in tentativas_exclusao:
            try:
                cloudinary.uploader.destroy(pid, invalidate=True, resource_type=rtype)
            except Exception:
                pass

        # Garante que o Django execute sua rotina de limpeza isolando possíveis erros.
        try:
            super().delete(name)
        except Exception:
            pass