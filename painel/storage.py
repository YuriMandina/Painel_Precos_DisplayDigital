# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
import logging
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from cloudinary_storage.storage import MediaCloudinaryStorage

logger = logging.getLogger(__name__)

# ==============================================================================
#                             STORAGE CUSTOMIZADO
# ==============================================================================
class MidiaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Storage inteligente para mídias (vídeos e imagens).

    Problema que resolve:
    ---------------------
    A biblioteca `django-cloudinary-storage` tem bugs com vídeos:
    1. Ao salvar, o Cloudinary retorna apenas o `public_id` (sem extensão).
       Isso quebra nossa detecção de tipo (vídeo vs imagem) que depende da extensão.
    2. O método `url()` padrão da biblioteca frequentemente gera URLs erradas
       para vídeos, usando `resource_type=image` ao invés de `resource_type=video`.

    Solução:
    --------
    - `_save()`: Intercepta o retorno e força a extensão original de volta ao nome.
    - `url()`: Usa cloudinary.utils.cloudinary_url() — a API oficial — para gerar
               a URL correta com o resource_type adequado (video/image).
    - `delete()`: Usa cloudinary.uploader.destroy() direto para não depender da lib.
    """
    RESOURCE_TYPE = 'auto'

    # Extensões que identificamos como vídeo
    VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.ogg', '.mkv', '.m4v', '.flv'}

    def _get_resource_type(self, name: str) -> str:
        """Determina o resource_type correto baseado na extensão do arquivo."""
        ext = os.path.splitext(name)[1].lower()
        return 'video' if ext in self.VIDEO_EXTENSIONS else 'image'

    def _save(self, name, content):
        """
        GATILHO DE CORREÇÃO: Intercepta o retorno do Cloudinary antes de salvar no banco.

        O Cloudinary retorna apenas o `public_id` (sem extensão) após o upload.
        Nós forçamos a extensão original de volta para que nossa lógica de
        detecção de tipo (vídeo vs imagem) continue funcionando corretamente.
        """
        # 1. Faz o upload via biblioteca padrão (usa RESOURCE_TYPE='auto')
        saved_name = super()._save(name, content)

        # 2. Resgata a extensão original do arquivo que estava sendo feito o upload
        extensao = os.path.splitext(content.name)[1].lower()

        # 3. Reconecta a extensão ao nome que vai para o banco (se já não a possuir)
        if extensao and not saved_name.lower().endswith(extensao):
            saved_name = f"{saved_name}{extensao}"

        logger.info(f"[Storage] Arquivo salvo no Cloudinary: {saved_name}")
        return saved_name

    def url(self, name: str) -> str:
        """
        Gera a URL pública do Cloudinary usando o SDK oficial.

        Por que não construir a URL manualmente?
        - O SDK garante o formato correto para todos os resource_types.
        - Lida automaticamente com pastas, versões e transformações.
        - Evita erros sutis como public_id com/sem extensão.

        Formato do `name` salvo no banco: 'midias/nome-do-arquivo.mp4'
        O public_id para o Cloudinary é: 'midias/nome-do-arquivo' (sem extensão)
        A extensão/formato é passada como parâmetro separado para o SDK.
        """
        if not name:
            return ""

        resource_type = self._get_resource_type(name)

        # O public_id no Cloudinary NÃO inclui a extensão
        public_id = os.path.splitext(name)[0]
        extensao = os.path.splitext(name)[1].lstrip('.')  # ex: 'mp4', 'jpg'

        # Usa o SDK do Cloudinary para gerar a URL correta
        url, _ = cloudinary.utils.cloudinary_url(
            public_id,
            resource_type=resource_type,
            format=extensao if extensao else None,
            secure=True,  # Sempre HTTPS
        )

        logger.debug(f"[Storage] URL gerada para '{name}': {url}")
        return url

    def delete(self, name: str) -> None:
        """Localiza o vínculo exato do arquivo para destruição na nuvem."""
        if not name:
            return

        resource_type = self._get_resource_type(name)
        public_id = os.path.splitext(name)[0]

        try:
            result = cloudinary.uploader.destroy(
                public_id,
                resource_type=resource_type,
                invalidate=True
            )
            logger.info(f"[Storage] Arquivo destruído no Cloudinary: {public_id} ({resource_type}) → {result}")
        except Exception as e:
            logger.error(f"[Storage] Falha ao destruir arquivo na nuvem: {e}")

        try:
            super().delete(name)
        except Exception:
            pass