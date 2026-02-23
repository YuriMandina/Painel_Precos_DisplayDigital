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
    
    # Avisa ao Cloudinary para aceitar TUDO.
    # Ao alterar para 'auto', o Cloudinary examina o arquivo no momento do 
    # upload e decide sozinho.
    RESOURCE_TYPE = 'auto'
    
    def url(self, name: str) -> str:
        """
        Corrige o link de entrega/reprodução da mídia.
        Como usamos 'auto' no upload, a biblioteca gera URLs com '/auto/upload/'.
        O Cloudinary exige que a rota final seja '/video/' ou '/image/' para tocar.
        """
        url_gerada = super().url(name)
        
        if not name:
            return url_gerada
            
        extensao = os.path.splitext(name)[1].lower()
        
        if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv']:
            # Traduz a rota para o formato de entrega de vídeo
            return url_gerada.replace('/auto/upload/', '/video/upload/', 1)
        else:
            # Traduz a rota para o formato de entrega de imagem
            return url_gerada.replace('/auto/upload/', '/image/upload/', 1)

    def delete(self, name: str) -> None:
        """
        Garante a exclusão física do arquivo no Cloudinary quando deletado no Painel.
        A API oficial de deleção não suporta 'auto', então forçamos o tipo correto.
        """
        if not name:
            return
            
        extensao = os.path.splitext(name)[1].lower()
        res_type = 'video' if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv'] else 'image'
        
        # Pega a chave do arquivo (sem a extensão) usada internamente pelo Cloudinary
        public_id = self._get_public_id(name)
        
        try:
            cloudinary.uploader.destroy(
                public_id, 
                invalidate=True, 
                resource_type=res_type
            )
        except Exception:
            # Previne erro 500 caso a mídia já não exista mais no Cloudinary
            # por conta de alguma exclusão manual prévia.
            pass