from rest_framework import serializers
from .models import Produto, FamiliaProduto, VideoTemplate, Dispositivo

class FamiliaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamiliaProduto
        fields = ['id', 'nome']


class VideoTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoTemplate
        fields = '__all__'


class ProdutoSerializer(serializers.ModelSerializer):
    # Campos calculados ou aninhados (Read-Only)
    familia_nome = serializers.CharField(source='familia.nome', read_only=True)
    template_video = VideoTemplateSerializer(read_only=True)

    class Meta:
        model = Produto
        fields = [
            'codigo',
            'descricao',
            'preco',
            'familia',       # ID para filtros/relacionamentos
            'familia_nome',  # String para exibição
            'imagem',
            'em_oferta',
            'template_video',
            'ordem'
        ]


class DispositivoConfigSerializer(serializers.ModelSerializer):
    """
    Serializer para configuração inicial do dispositivo (TV).
    Define identidade e modo de operação.
    """
    class Meta:
        model = Dispositivo
        fields = [
            'nome',
            'modo_exibicao',
            'uuid',
            'orientacao'
        ]