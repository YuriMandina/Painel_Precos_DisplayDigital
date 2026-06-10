# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
import uuid
import random
import string

from django.db import models
from django.contrib.auth.models import User


# ==============================================================================
#                             FUNÇÕES AUXILIARES
# ==============================================================================

def gerar_codigo_curto() -> str:
    """
    Gera um código alfanumérico aleatório de 6 caracteres.
    Utilizado primariamente para geração de tokens de pareamento de dispositivos.
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# ==============================================================================
#                                 MODELOS
# ==============================================================================

class Empresa(models.Model):
    """
    Modelo base de isolamento lógico (Tenant).
    Centraliza todos os relacionamentos de dados do sistema por cliente.
    """
    nome = models.CharField(max_length=150, help_text="Razão social ou nome fantasia da empresa.")
    cnpj = models.CharField(max_length=20, blank=True, null=True)
    ativo = models.BooleanField(default=True)
    
    # Integração Omie
    omie_app_key = models.CharField(max_length=255, blank=True, null=True, help_text="App Key gerada no painel do Omie")
    omie_app_secret = models.CharField(max_length=255, blank=True, null=True, help_text="App Secret gerado no painel do Omie")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self) -> str:
        return self.nome


class Perfil(models.Model):
    """
    Extensão do modelo padrão de User do Django (1:1).
    Estabelece a autorização baseada em Tenant (Empresa) para cada usuário.
    """
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Aguardando Aprovação'
        APROVADO = 'APROVADO', 'Aprovado'

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='usuarios')
    
    is_admin = models.BooleanField(default=False, help_text="Usuário master/dono da conta")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"

    def __str__(self) -> str:
        return f"{self.usuario.username} ({self.empresa.nome}) - {self.status}"


class Convite(models.Model):
    """
    Representa um convite de acesso pendente para um usuário ingressar na empresa.
    """
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        ACEITO = 'ACEITO', 'Aceito'

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='convites')
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Convite"
        verbose_name_plural = "Convites"
        unique_together = ('empresa', 'email')

    def __str__(self) -> str:
        return f"Convite para {self.email} ({self.status})"


class TokenVerificacaoEmail(models.Model):
    """
    Token de verificação de email gerado no momento do cadastro.
    O usuário recebe um link com este token por email. Ao clicar,
    o campo is_active do User é ativado e o token é expirado.
    """
    usuario = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='token_verificacao_email'
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    usado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Token de Verificação de Email"
        verbose_name_plural = "Tokens de Verificação de Email"

    def __str__(self) -> str:
        return f"Token de verificação para {self.usuario.email}"

    def esta_expirado(self) -> bool:
        """Tokens expiram em 48 horas."""
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > self.criado_em + timedelta(hours=48)


# ==============================================================================
#                             CATÁLOGO E PRODUTOS
# ==============================================================================

class SincronizacaoOmie(models.Model):
    """
    Armazena o payload temporário da API do Omie para o fluxo de validação
    em duas etapas (Preview -> Efetivação).
    """
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente de Aprovação'
        CONCLUIDA = 'CONCLUIDA', 'Concluída'
        ERRO = 'ERRO', 'Erro na Sincronização'

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='sincronizacoes_omie')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    dados = models.JSONField(
        default=dict, 
        help_text="Payload JSON processado contendo os novos produtos, alterações de preço, etc."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sincronização Omie"
        verbose_name_plural = "Sincronizações Omie"
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Sync Omie {self.id} - {self.empresa.nome} ({self.get_status_display()})"


class ProdutoIgnoradoOmie(models.Model):
    """
    Deny List de produtos: Itens que vieram do Omie, mas o usuário marcou para 
    ignorar permanentemente para não poluírem a lista de validação.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='produtos_ignorados_omie')
    codigo = models.CharField(max_length=50, db_index=True, help_text="Código do produto no ERP")
    descricao = models.CharField(max_length=255, blank=True, null=True, help_text="Nome do produto no momento em que foi ignorado")
    familia = models.CharField(max_length=150, blank=True, null=True, help_text="Família do produto no momento em que foi ignorado")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Produto Ignorado Omie"
        verbose_name_plural = "Produtos Ignorados Omie"
        unique_together = ('empresa', 'codigo')

    def __str__(self) -> str:
        return f"{self.codigo} (Ignorado em {self.empresa.nome})"

class FamiliaProduto(models.Model):
    """
    Agrupamento lógico de produtos (Categorias).
    Sincronizado via integração com ERPs, restrito ao escopo da Empresa.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='familias')
    nome = models.CharField(max_length=100, help_text="Nomenclatura da categoria/família originada do ERP.")

    class Meta:
        verbose_name = "Família de Produto"
        verbose_name_plural = "Famílias de Produtos"
        unique_together = ('empresa', 'nome')

    def __str__(self) -> str:
        return self.nome


class Produto(models.Model):
    """
    Entidade principal de exibição.
    Armazena dados transacionais (preço) e metadados de UI (ordem, imagem, oferta).
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='produtos')
    familia = models.ForeignKey(FamiliaProduto, on_delete=models.CASCADE, related_name='produtos')
    
    codigo = models.CharField(max_length=50, db_index=True)
    descricao = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    
    ordem = models.IntegerField(default=0, help_text="Peso de ordenação na renderização UI (Crescente).")
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True)
    em_oferta = models.BooleanField(default=False)
    exibir_no_painel = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['descricao']
        unique_together = ('empresa', 'codigo')

    def __str__(self) -> str:
        return f"{self.codigo} - {self.descricao}"


# ==============================================================================
#                             LISTAS PERSONALIZADAS
# ==============================================================================

class ListaPersonalizada(models.Model):
    """
    Agrupamento manual de produtos com ordenação arbitrária.
    Permite definir um header (nome) personalizado para exibição na TV.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='listas_personalizadas')
    nome = models.CharField(max_length=150, help_text="Título customizado que aparecerá no cabeçalho da TV.")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lista Personalizada"
        verbose_name_plural = "Listas Personalizadas"

    def __str__(self) -> str:
        return self.nome


class ListaProduto(models.Model):
    """
    Tabela de junção (Through) para armazenar os produtos de uma lista
    e sua ordenação estrita.
    """
    lista = models.ForeignKey(ListaPersonalizada, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    ordem = models.IntegerField(default=0, help_text="Posição do produto dentro da lista")

    class Meta:
        ordering = ['ordem']
        unique_together = ('lista', 'produto')

    def __str__(self) -> str:
        return f"{self.produto.descricao} na lista {self.lista.nome}"


# ==============================================================================
#                             MÍDIA E CONTEÚDO
# ==============================================================================

class Midia(models.Model):
    """
    Repositório de assets estáticos (Vídeos e Imagens) vinculados a uma empresa
    para utilização em Playlists e campanhas.
    """
    class Tipo(models.TextChoices):
        VIDEO = 'VIDEO', 'Vídeo'
        IMAGEM = 'IMAGEM', 'Imagem'

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='midias')
    
    nome = models.CharField(max_length=100, help_text="Identificador interno do asset.")
    arquivo = models.FileField(upload_to='midias/')
    tipo = models.CharField(max_length=10, choices=Tipo.choices, editable=False)
    duracao = models.IntegerField(default=15, help_text="Tempo de exibição (TTL) em segundos no client.")
    
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs) -> None:
        """
        Gatilho pré-salvamento para inferência automática do tipo MIME 
        baseado na extensão do payload do arquivo.
        """
        if self.arquivo:
            ext = os.path.splitext(self.arquivo.name)[1].lower()
            if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
                self.tipo = self.Tipo.IMAGEM
            else:
                self.tipo = self.Tipo.VIDEO
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> None:
        """
        Gatilho ativado ao excluir a mídia. 
        Força a exclusão física do arquivo lá no Cloudinary para não gerar lixo.
        """
        if self.arquivo:
            self.arquivo.delete(save=False) # Dispara o delete() do nosso storage.py
        super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.nome} ({self.get_tipo_display()})"


# ==============================================================================
#                             DISPOSITIVOS E TELAS
# ==============================================================================

class Dispositivo(models.Model):
    """
    Representação lógica de um endpoint físico (TV/Monitor) em execução.
    Gerencia credenciais de pareamento, layout e fila de reprodução (Playlist).
    """
    class Orientacao(models.TextChoices):
        HORIZONTAL = 'HORIZONTAL', 'Horizontal (Padrão 16:9)'
        VERTICAL_DIR = 'VERTICAL_DIR', 'Vertical 9:16 (Giro 90° Direita)'
        VERTICAL_ESQ = 'VERTICAL_ESQ', 'Vertical 9:16 (Giro 90° Esquerda)'

    class ModoExibicao(models.TextChoices):
        TABELA = 'TABELA', 'Apenas Tabela de Preços'
        VIDEO = 'VIDEO', 'Apenas Mídia'
        MISTO = 'MISTO', 'Híbrido (Legado)'
        PLAYLIST = 'PLAYLIST', 'Playlist Personalizada'

    # Relacionamentos e Identificação
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='dispositivos')
    nome = models.CharField(max_length=100, help_text="Identificação do local físico do dispositivo.")
    titulo_exibicao = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Header de exibição na UI. Faz fallback para o campo 'nome' se nulo."
    )

    # Segurança e Autenticação
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    codigo_acesso = models.CharField(
        max_length=6, 
        default=gerar_codigo_curto, 
        unique=True, 
        editable=False
    )

    # Regras de Negócio e Conteúdo
    exibir_apenas_familias = models.ManyToManyField(FamiliaProduto, blank=True)
    playlist = models.JSONField(
        default=list, 
        blank=True, 
        help_text="Estrutura de dados serializada contendo a fila de mídias e tabelas."
    )

    # Renderização (Client-side)
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

    def __str__(self) -> str:
        return f"{self.nome} ({self.get_orientacao_display()})"