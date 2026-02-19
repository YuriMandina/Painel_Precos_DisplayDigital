import uuid
import random
import string
import os
from django.db import models
from django.core.exceptions import ValidationError

def gerar_codigo_curto():
    """Gera um código alfanumérico de 6 caracteres para pareamento."""
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


class Midia(models.Model):
    """
    Biblioteca de Mídia (Vídeos e Imagens).
    Armazena os arquivos que podem ser inseridos nas playlists das TVs.
    """
    class Tipo(models.TextChoices):
        VIDEO = 'VIDEO', 'Vídeo'
        IMAGEM = 'IMAGEM', 'Imagem'

    nome = models.CharField(max_length=100, help_text="Identificação interna para organização")
    
    arquivo = models.FileField(upload_to='midias/')
    
    tipo = models.CharField(max_length=10, choices=Tipo.choices, editable=False)
    duracao = models.IntegerField(default=15, help_text="Duração padrão em segundos para exibição")
    
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Define automaticamente o tipo baseando-se na extensão do arquivo
        if self.arquivo:
            ext = os.path.splitext(self.arquivo.name)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                self.tipo = self.Tipo.IMAGEM
            else:
                self.tipo = self.Tipo.VIDEO
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class Produto(models.Model):
    """Produto principal importado e exibido nas telas (Tabela de Preços)."""
    codigo = models.CharField(max_length=50, unique=True, db_index=True)
    descricao = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    
    familia = models.ForeignKey(
        FamiliaProduto,
        on_delete=models.CASCADE,
        related_name='produtos'
    )
    
    # Configurações de Exibição
    ordem = models.IntegerField(
        default=0,
        help_text="Ordem de exibição na TV (Menor número aparece primeiro)"
    )
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True)
    em_oferta = models.BooleanField(default=False)
    exibir_no_painel = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['descricao']

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"


class Dispositivo(models.Model):
    """Representa uma TV ou painel físico conectado ao sistema."""
    
    class Orientacao(models.TextChoices):
        HORIZONTAL = 'HORIZONTAL', 'Horizontal (Padrão 16:9)'
        VERTICAL_DIR = 'VERTICAL_DIR', 'Vertical 9:16 (Giro 90° Direita)'
        VERTICAL_ESQ = 'VERTICAL_ESQ', 'Vertical 9:16 (Giro 90° Esquerda)'

    class ModoExibicao(models.TextChoices):
        TABELA = 'TABELA', 'Apenas Tabela de Preços'
        VIDEO = 'VIDEO', 'Apenas Mídia'
        MISTO = 'MISTO', 'Híbrido (Legado)'
        PLAYLIST = 'PLAYLIST', 'Playlist Personalizada'

    nome = models.CharField(max_length=100, help_text="Ex: TV do Açougue")
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
    
    playlist = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista ordenada de itens (Mídias e Tabelas) para reprodução."
    )

    # Configurações de Display
    orientacao = models.CharField(
        max_length=20,
        choices=Orientacao.choices,
        default=Orientacao.HORIZONTAL
    )
    modo_exibicao = models.CharField(
        max_length=20,
        choices=ModoExibicao.choices,
        default=ModoExibicao.PLAYLIST
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({self.get_orientacao_display()})"