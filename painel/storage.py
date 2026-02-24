# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
import logging
import cloudinary
import cloudinary.uploader
from cloudinary_storage.storage import MediaCloudinaryStorage

logger = logging.getLogger(__name__)

# ==============================================================================
#                             STORAGE CUSTOMIZADO
# ==============================================================================
class MidiaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Storage inteligente. Usa a biblioteca apenas para o Upload.
    A leitura (URL) e a Exclusão (Delete) são feitas via acesso direto à API 
    para contornar bugs de roteamento de vídeos da biblioteca padrão.
    """
    RESOURCE_TYPE = 'auto'
    
    def url(self, name: str) -> str:
        """Constrói o vínculo (link) exato de forma determinística."""
        if not name:
            return ""
            
        # Pegamos o nome da sua nuvem direto das configurações já carregadas
        cloud_name = cloudinary.config().cloud_name
        
        extensao = os.path.splitext(name)[1].lower()
        is_video = extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv']
        res_type = 'video' if is_video else 'image'
        
        # SOLUÇÃO DO VÍNCULO: Construímos a URL bruta e garantida do Cloudinary.
        # name carrega o caminho do banco do Django (ex: midias/meuvideo.mp4)
        url_direta = f"https://res.cloudinary.com/{cloud_name}/{res_type}/upload/{name}"
        
        return url_direta

    def delete(self, name: str) -> None:
        """Localiza o vínculo exato do arquivo para destruição na nuvem."""
        if not name:
            return
            
        extensao = os.path.splitext(name)[1].lower()
        is_video = extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv']
        res_type = 'video' if is_video else 'image'
        
        # O Cloudinary salva o identificador (public_id) sempre SEM a extensão
        public_id = os.path.splitext(name)[0]
        
        # Ataque direto à API do Cloudinary com o ID e o Tipo corretos
        try:
            cloudinary.uploader.destroy(public_id, resource_type=res_type, invalidate=True)
            logger.info(f"Vínculo destruído no Cloudinary: {public_id} ({res_type})")
        except Exception as e:
            logger.error(f"Falha ao romper vínculo na nuvem: {e}")

        # Limpeza do registro local do Django
        try:
            super().delete(name)
        except Exception:
            pass