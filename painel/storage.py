# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
import cloudinary.uploader
import cloudinary.utils
from cloudinary_storage.storage import MediaCloudinaryStorage


# ==============================================================================
#                             STORAGE CUSTOMIZADO
# ==============================================================================
class MidiaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Storage blindado que corrige três falhas críticas:
    1. Quebra da biblioteca padrão ao lidar com vídeos e imagens no mesmo campo.
    2. Erro 500 (DataError) por nomes de arquivos maiores que 100 caracteres.
    3. Quebra de URLs de reprodução por inferência errada de rotas (/image vs /video).
    """
    
    def _save(self, name, content):
        """Intercepta o arquivo antes de subir para a nuvem."""
        nome_base, extensao = os.path.splitext(name)
        extensao = extensao.lower()
        
        # BLINDAGEM DO BANCO DE DADOS (Corta nomes gigantes)
        # Limita o nome para no máximo 30 caracteres para caber confortavelmente 
        # nos 100 caracteres do banco Neon após o Cloudinary inserir os hashes.
        nome_curto = nome_base[:30] 
        name_seguro = self._normalise_name(f"{nome_curto}{extensao}")
        name_seguro = self._prepend_prefix(name_seguro)
        
        # 2. DEFINIÇÃO ESTRITA DE ROTA
        is_video = extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv']
        res_type = 'video' if is_video else 'image'
        
        # Configura as opções dinamicamente
        options = {
            'resource_type': res_type,
            'tags': self.TAGS,
        }
        if hasattr(self, 'FOLDER') and self.FOLDER:
            options['folder'] = self.FOLDER
            
        # 3. UPLOAD LIMPO USANDO A API OFICIAL
        response = cloudinary.uploader.upload(content.file, **options)
        
        # Retorna a string exata que será salva no banco (segura e com a extensão)
        return f"{response['public_id']}{extensao}"


    def url(self, name: str) -> str:
        """Gera a URL de reprodução direta sem as quebras de '/image/' da biblioteca."""
        if not name:
            return ''
            
        extensao = os.path.splitext(name)[1].lower()
        res_type = 'video' if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv'] else 'image'
        
        # Constrói o link perfeitamente configurado e forçando HTTPS
        url_gerada, _ = cloudinary.utils.cloudinary_url(
            name, 
            resource_type=res_type,
            secure=True
        )
        return url_gerada


    def delete(self, name: str) -> None:
        """Garante a lixeira limpa na nuvem quando a mídia for deletada no painel."""
        if not name:
            return
            
        extensao = os.path.splitext(name)[1].lower()
        res_type = 'video' if extensao in ['.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv'] else 'image'
        
        public_id = self._get_public_id(name)
        
        try:
            cloudinary.uploader.destroy(public_id, resource_type=res_type, invalidate=True)
        except Exception:
            pass