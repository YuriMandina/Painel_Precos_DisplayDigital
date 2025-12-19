import uuid
import random
import string
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
    nome = models.CharField(max_length=100)
    arquivo_video = models.FileField(upload_to='templates_video/')

    titulo_top = models.FloatField(default=10, validators=[validar_porcentagem])
    titulo_left = models.FloatField(default=50, validators=[validar_porcentagem])
    titulo_cor = models.CharField(max_length=7, default="#FFFFFF")
    titulo_tamanho = models.CharField(max_length=10, default="5vw")

    preco_top = models.FloatField(default=50, validators=[validar_porcentagem])
    preco_left = models.FloatField(default=50, validators=[validar_porcentagem])
    preco_cor = models.CharField(max_length=7, default="#FFD700")
    preco_tamanho = models.CharField(max_length=10, default="8vw")

    img_top = models.FloatField(default=30, validators=[validar_porcentagem])
    img_left = models.FloatField(default=10, validators=[validar_porcentagem])
    img_width = models.FloatField(default=20, validators=[validar_porcentagem])

    duracao = models.IntegerField(default=15, help_text="Duração do vídeo em segundos (Padrão para produtos)")

    estilos_css = models.JSONField(default=dict, blank=True)
    elementos_extras = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.nome

class VideoPropaganda(models.Model):
    """
    Vídeos institucionais ou de parceiros que não dependem de um produto.
    """
    descricao = models.CharField(max_length=100, help_text="Nome interno para identificação")
    arquivo_video = models.FileField(upload_to='propagandas/')
    duracao = models.IntegerField(default=15, help_text="Duração em segundos (caso o vídeo não tenha metadados)")
    ativo = models.BooleanField(default=True)
    duracao = models.IntegerField(default=15, help_text="Duração em segundos")
    ordem = models.IntegerField(default=0, help_text="Ordem de exibição na playlist")
    ativo = models.BooleanField(default=True, help_text="Se desmarcado, não aparecerá na TV")

    def __str__(self):
        return f"{self.descricao} ({self.duracao}s)"

class Produto(models.Model):
    """
    O produto principal. A importação do Excel vai popular isso.
    """
    codigo = models.CharField(max_length=50, unique=True, db_index=True)
    descricao = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    familia = models.ForeignKey(FamiliaProduto, on_delete=models.CASCADE, related_name='produtos')
    ordem = models.IntegerField(default=0, help_text="Ordem de exibição na TV (Menor número aparece primeiro)")
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


def gerar_codigo_curto():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

class Dispositivo(models.Model):
    nome = models.CharField(max_length=100, help_text="Ex: TV do Açougue")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    codigo_acesso = models.CharField(max_length=6, default=gerar_codigo_curto, unique=True, editable=False)

    exibir_apenas_familias = models.ManyToManyField(FamiliaProduto, blank=True)
    exibir_propagandas = models.ManyToManyField(VideoPropaganda, blank=True, help_text="Selecione vídeos institucionais para intercalar")
    orientacao = models.CharField(max_length=20, choices=[
        ('HORIZONTAL', 'Horizontal (Padrão 16:9)'),
        ('VERTICAL_DIR', 'Vertical 9:16 (Giro 90° Direita)'),
        ('VERTICAL_ESQ', 'Vertical 9:16 (Giro 90° Esquerda)')
    ], default='HORIZONTAL', help_text="Escolha conforme a instalação física da TV")

    modo_exibicao = models.CharField(max_length=20, choices=[
        ('TABELA', 'Apenas Tabela de Preços'),
        ('VIDEO', 'Apenas Vídeos de Oferta'),
        ('MISTO', 'Tabela + Vídeos Intercalados')
    ], default='TABELA')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({self.get_orientacao_display()})"