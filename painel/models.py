import uuid
import random
import string
import os
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


class Midia(models.Model):
    """
    Entidade central para conteúdos de sinalização.
    Serve como container para as camadas (Layers) do editor visual.
    """
    class Tipo(models.TextChoices):
        VIDEO = 'VIDEO', 'Vídeo'
        IMAGEM = 'IMAGEM', 'Imagem'

    nome = models.CharField(max_length=100, help_text="Identificação interna para organização")
    
    # Arquivo base (Background padrão ou renderização final)
    arquivo = models.FileField(upload_to='midias/')
    
    tipo = models.CharField(max_length=10, choices=Tipo.choices, editable=False)
    duracao = models.IntegerField(default=15, help_text="Duração em segundos (padrão)")
    
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Lógica pragmática: define tipo pela extensão
        if self.arquivo:
            ext = os.path.splitext(self.arquivo.name)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                self.tipo = self.Tipo.IMAGEM
            else:
                self.tipo = self.Tipo.VIDEO
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class Layer(models.Model):
    """
    Representa uma camada visual no editor (Texto, Imagem, Shape ou Grupo).
    Suporta aninhamento (grupos) e configurações flexíveis via JSON.
    """
    class LayerType(models.TextChoices):
        TEXT = 'TEXT', 'Texto'
        IMAGE = 'IMAGE', 'Imagem'
        VIDEO = 'VIDEO', 'Vídeo'
        SHAPE = 'SHAPE', 'Forma'
        GROUP = 'GROUP', 'Grupo'

    midia = models.ForeignKey(
        Midia, 
        on_delete=models.CASCADE, 
        related_name='layers',
        help_text="Mídia (Canvas) onde esta camada está inserida"
    )
    
    # Hierarquia para suportar Grupos
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE, 
        related_name='children',
        help_text="Camada pai, caso esta camada pertença a um grupo"
    )

    tipo = models.CharField(max_length=10, choices=LayerType.choices, default=LayerType.TEXT)
    
    # Armazena propriedades visuais variáveis (x, y, width, height, color, font, src, etc)
    config = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Propriedades visuais e comportamentais da camada"
    )
    
    # Controle de exibição e edição
    z_index = models.IntegerField(default=0, help_text="Ordem de empilhamento (maior fica por cima)")
    is_locked = models.BooleanField(default=False, help_text="Bloqueia edição no editor visual")
    is_visible = models.BooleanField(default=True, help_text="Define se a camada é renderizada")

    class Meta:
        ordering = ['z_index']
        verbose_name = "Camada"
        verbose_name_plural = "Camadas"

    def __str__(self):
        return f"{self.get_tipo_display()} (Z: {self.z_index}) - {self.midia.nome}"


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