import uuid
import random
import string
from django.db import models
from django.core.exceptions import ValidationError

def validar_porcentagem(value):
    """Valida se o valor está entre 0 e 100."""
    if value < 0 or value > 100:
        raise ValidationError('O valor deve estar entre 0 e 100 (representando a % da tela).')

def gerar_codigo_curto():
    """Gera um código alfanumérico de 6 caracteres."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class FamiliaProduto(models.Model):
    """
    Categorias de produtos vindas do ERP (Ex: BOVINOS, AVÍCOLAS).
    Utilizado para filtrar o conteúdo exibido em cada TV.
    """
    nome = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nome da categoria vinda do ERP"
    )

    class Meta:
        verbose_name = "Família de Produto"
        verbose_name_plural = "Famílias de Produtos"

    def __str__(self):
        return self.nome


class VideoTemplate(models.Model):
    """Define o layout visual para vídeos de produtos."""
    nome = models.CharField(max_length=100)
    arquivo_video = models.FileField(upload_to='templates_video/')
    duracao = models.IntegerField(
        default=15,
        help_text="Duração do vídeo em segundos (Padrão para produtos)"
    )

    # --- Configuração do Título ---
    titulo_top = models.FloatField(default=10, validators=[validar_porcentagem])
    titulo_left = models.FloatField(default=50, validators=[validar_porcentagem])
    titulo_cor = models.CharField(max_length=7, default="#FFFFFF")
    titulo_tamanho = models.CharField(max_length=10, default="5vw")

    # --- Configuração do Preço ---
    preco_top = models.FloatField(default=50, validators=[validar_porcentagem])
    preco_left = models.FloatField(default=50, validators=[validar_porcentagem])
    preco_cor = models.CharField(max_length=7, default="#FFD700")
    preco_tamanho = models.CharField(max_length=10, default="8vw")

    # --- Configuração da Imagem ---
    img_top = models.FloatField(default=30, validators=[validar_porcentagem])
    img_left = models.FloatField(default=10, validators=[validar_porcentagem])
    img_width = models.FloatField(default=20, validators=[validar_porcentagem])

    # --- Extras ---
    estilos_css = models.JSONField(default=dict, blank=True)
    elementos_extras = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.nome


class VideoPropaganda(models.Model):
    """Vídeos institucionais ou de parceiros independentes de produtos."""
    descricao = models.CharField(max_length=100, help_text="Nome interno para identificação")
    arquivo_video = models.FileField(upload_to='propagandas/')
    duracao = models.IntegerField(default=15, help_text="Duração em segundos")
    ordem = models.IntegerField(default=0, help_text="Ordem de exibição na playlist")
    ativo = models.BooleanField(default=True, help_text="Se desmarcado, não aparecerá na TV")

    def __str__(self):
        return f"{self.descricao} ({self.duracao}s)"


class Produto(models.Model):
    """Produto principal importado e exibido nas telas."""
    codigo = models.CharField(max_length=50, unique=True, db_index=True)
    descricao = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    
    familia = models.ForeignKey(
        FamiliaProduto,
        on_delete=models.CASCADE,
        related_name='produtos'
    )
    
    # Exibição
    ordem = models.IntegerField(
        default=0,
        help_text="Ordem de exibição na TV (Menor número aparece primeiro)"
    )
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True)
    em_oferta = models.BooleanField(default=False)
    exibir_no_painel = models.BooleanField(default=True)

    # Template Vinculado
    template_video = models.ForeignKey(
        VideoTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Selecione um template para exibir este produto como oferta em vídeo"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['descricao']

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"


class Dispositivo(models.Model):
    """Representa uma TV ou painel físico."""
    
    class Orientacao(models.TextChoices):
        HORIZONTAL = 'HORIZONTAL', 'Horizontal (Padrão 16:9)'
        VERTICAL_DIR = 'VERTICAL_DIR', 'Vertical 9:16 (Giro 90° Direita)'
        VERTICAL_ESQ = 'VERTICAL_ESQ', 'Vertical 9:16 (Giro 90° Esquerda)'

    class ModoExibicao(models.TextChoices):
        TABELA = 'TABELA', 'Apenas Tabela de Preços (Legado)'
        VIDEO = 'VIDEO', 'Apenas Vídeos de Oferta (Legado)'
        MISTO = 'MISTO', 'Tabela + Vídeos Intercalados (Legado)'
        PLAYLIST = 'PLAYLIST', 'Usar Playlist Personalizada (Nova)'

    nome = models.CharField(max_length=100, help_text="Ex: TV do Açougue (Identificação Interna)")
    titulo_exibicao = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Título exibido no topo da TV. Se vazio, usa o Nome."
    )

    # Identificação e Segurança
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    codigo_acesso = models.CharField(
        max_length=6,
        default=gerar_codigo_curto,
        unique=True,
        editable=False
    )

    # Conteúdo
    exibir_apenas_familias = models.ManyToManyField(FamiliaProduto, blank=True)
    exibir_propagandas = models.ManyToManyField(
        VideoPropaganda,
        blank=True,
        help_text="Selecione vídeos institucionais para intercalar"
    )
    playlist = models.JSONField(
        default=list,
        blank=True,
        help_text="Estrutura ordenada da playlist (Drag & Drop)"
    )

    # Configurações de Display
    orientacao = models.CharField(
        max_length=20,
        choices=Orientacao.choices,
        default=Orientacao.HORIZONTAL,
        help_text="Escolha conforme a instalação física da TV"
    )
    modo_exibicao = models.CharField(
        max_length=20,
        choices=ModoExibicao.choices,
        default=ModoExibicao.PLAYLIST
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({self.get_orientacao_display()})"