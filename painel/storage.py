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

    def _save(self, name, content):
        """
        GATILHO DE CORREÇÃO: Intercepta o retorno do Cloudinary antes de salvar no banco.
        Como o Cloudinary retorna apenas o 'public_id' (sem extensão), nós forçamos
        a extensão original de volta ao nome salvo para não quebrar nosso roteamento.
        """
        # 1. Faz o upload via biblioteca padrão
        saved_name = super()._save(name, content)
        
        # 2. Resgata a extensão original do arquivo que estava sendo feito o upload
        extensao = os.path.splitext(content.name)[1].lower()
        
        # 3. Reconecta a extensão ao nome que vai para o banco (se já não a possuir)
        if extensao and not saved_name.lower().endswith(extensao):
            saved_name = f"{saved_name}{extensao}"
            
        return saved_name
    
    def url(self, name: str) -> str:
        """Constrói o vínculo (link) exato de forma determinística."""
        if not name:
            return ""
            
        cloud_name = cloudinary.config().cloud_name
        
        extensao = os.path.splitext(name)[1].lower()
        is_video = extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv']
        res_type = 'video' if is_video else 'image'
        
        url_direta = f"https://res.cloudinary.com/{cloud_name}/{res_type}/upload/{name}"
        
        return url_direta

    def delete(self, name: str) -> None:
        """Localiza o vínculo exato do arquivo para destruição na nuvem."""
        if not name:
            return
            
        extensao = os.path.splitext(name)[1].lower()
        is_video = extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv']
        res_type = 'video' if is_video else 'image'
        
        public_id = os.path.splitext(name)[0]
        
        try:
            cloudinary.uploader.destroy(public_id, resource_type=res_type, invalidate=True)
            logger.info(f"Vínculo destruído no Cloudinary: {public_id} ({res_type})")
        except Exception as e:
            logger.error(f"Falha ao romper vínculo na nuvem: {e}")

        try:
            super().delete(name)
        except Exception:
            pass