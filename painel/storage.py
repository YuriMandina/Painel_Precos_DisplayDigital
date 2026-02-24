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
    RESOURCE_TYPE = 'auto'
    
    def url(self, name: str) -> str:
        """Corrige o link de entrega/reprodução da mídia para a TV e Prévia."""
        if not name:
            return ""
            
        url_gerada = super().url(name)
        
        # Força HTTPS para evitar bloqueio de "Mixed Content" no player
        if url_gerada.startswith('http://'):
            url_gerada = url_gerada.replace('http://', 'https://', 1)
            
        extensao = os.path.splitext(name)[1].lower()
        
        # Força o roteamento correto para o servidor de streaming do Cloudinary
        if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv']:
            if '/image/upload/' in url_gerada:
                url_gerada = url_gerada.replace('/image/upload/', '/video/upload/', 1)
            elif '/raw/upload/' in url_gerada:
                url_gerada = url_gerada.replace('/raw/upload/', '/video/upload/', 1)
                
        return url_gerada

    def delete(self, name: str) -> None:
        """Garante a exclusão física do arquivo no Cloudinary de forma resiliente."""
        if not name:
            return
            
        extensao = os.path.splitext(name)[1].lower()
        res_type = 'video' if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv'] else 'image'
        
        # O Cloudinary geralmente armazena o public_id sem a extensão final
        public_id_sem_ext = os.path.splitext(name)[0]
        
        # Varre todas as possíveis combinações de como o arquivo pode ter sido salvo.
        tentativas_exclusao = [
            (public_id_sem_ext, res_type),
            (name, res_type),
            (public_id_sem_ext, 'image'), 
            (name, 'image'),
            (public_id_sem_ext, 'raw'),
            (name, 'raw')
        ]
        
        for pid, rtype in tentativas_exclusao:
            try:
                resposta = cloudinary.uploader.destroy(pid, invalidate=True, resource_type=rtype)
                # Se apagou com sucesso, encerra o loop
                if resposta.get('result') == 'ok':
                    logger.info(f"Mídia excluída do Cloudinary com sucesso: {pid}")
                    break
            except Exception as e:
                logger.debug(f"Tentativa ignorada para {pid} ({rtype}): {e}")

        # Limpeza local no banco de dados do Django
        try:
            super().delete(name)
        except Exception:
            pass