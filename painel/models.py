import uuid
from django.db import models
from django.core.exceptions import ValidationError

# Validador simples para garantir que porcentagens fiquem entre 0 e 100
def validar_porcentagem(value):
    if value < 0 or value > 100:
        raise ValidationError('O valor deve estar entre 0 e 100 (representando a % da tela).')

class FamiliaProduto(models.Model):
    """
    Categorias vindas do ERP (Ex: BOVINOS, AVÍCOLAS).
    Serve para filtrar o que aparece em cada TV.
    """
    nome = models.CharField(max_length=100, unique=True, help_text="Nome da categoria vinda do ERP")
    
    class Meta:
        verbose_name = "Família de Produto"
        verbose_name_plural = "Famílias de Produtos"

    def __str__(self):
        return self.nome


class VideoTemplate(models.Model):
    """
    Define o layout do vídeo promocional.
    O vídeo roda no fundo e usamos coordenadas CSS (%) para posicionar texto/imagem por cima.
    """
    nome = models.CharField(max_length=100, help_text="Ex: Oferta Fundo Vermelho")
    arquivo_video = models.FileField(upload_to='templates_video/', help_text="Vídeo de fundo (MP4 leve)")
    
    # --- Coordenadas do Título do Produto ---
    titulo_top = models.IntegerField(default=10, validators=[validar_porcentagem], help_text="% do topo para o Título")
    titulo_left = models.IntegerField(default=50, validators=[validar_porcentagem], help_text="% da esquerda para o Título")
    titulo_cor = models.CharField(max_length=7, default="#FFFFFF", help_text="Cor Hexadecimal (Ex: #FFFFFF)")
    titulo_tamanho = models.CharField(max_length=10, default="5vw", help_text="Tamanho da fonte (ex: 5vw, 40px)")

    # --- Coordenadas do Preço ---
    preco_top = models.IntegerField(default=50, validators=[validar_porcentagem], help_text="% do topo para o Preço")
    preco_left = models.IntegerField(default=50, validators=[validar_porcentagem], help_text="% da esquerda para o Preço")
    preco_cor = models.CharField(max_length=7, default="#FFD700", help_text="Cor Hexadecimal (Ex: #FFD700)")
    preco_tamanho = models.CharField(max_length=10, default="8vw", help_text="Tamanho da fonte (ex: 8vw)")

    # --- Coordenadas da Imagem do Produto ---
    img_top = models.IntegerField(default=30, validators=[validar_porcentagem], help_text="% do topo para a Imagem")
    img_left = models.IntegerField(default=10, validators=[validar_porcentagem], help_text="% da esquerda para a Imagem")
    img_width = models.IntegerField(default=20, validators=[validar_porcentagem], help_text="Largura da imagem em % da tela")

    class Meta:
        verbose_name = "Template de Vídeo"
        verbose_name_plural = "Templates de Vídeo"

    def __str__(self):
        return self.nome


class Produto(models.Model):
    """
    O produto principal. A importação do Excel vai popular isso.
    """
    codigo = models.CharField(max_length=50, unique=True, db_index=True)
    descricao = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    familia = models.ForeignKey(FamiliaProduto, on_delete=models.CASCADE, related_name='produtos')
    
    # Imagem é opcional, pois nem todo produto terá foto para o vídeo
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True)
    
    em_oferta = models.BooleanField(default=False)
    exibir_no_painel = models.BooleanField(default=True)
    
    # Vincula este produto a um template específico se ele for ser destaque em vídeo
    template_video = models.ForeignKey(VideoTemplate, on_delete=models.SET_NULL, null=True, blank=True, help_text="Selecione um template para exibir este produto como oferta em vídeo")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['descricao']

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"


class Dispositivo(models.Model):
    """
    Gerencia o pareamento das TVs.
    """
    nome = models.CharField(max_length=100, help_text="Ex: TV do Açougue")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # O que essa TV deve mostrar?
    exibir_apenas_familias = models.ManyToManyField(FamiliaProduto, blank=True, help_text="Se vazio, mostra tudo. Se selecionado, filtra apenas essas categorias.")
    
    modo_exibicao = models.CharField(max_length=20, choices=[
        ('TABELA', 'Apenas Tabela de Preços'),
        ('VIDEO', 'Apenas Vídeos de Oferta'),
        ('MISTO', 'Tabela + Vídeos Intercalados')
    ], default='TABELA')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({str(self.uuid)[:8]})"