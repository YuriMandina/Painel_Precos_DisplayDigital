from rest_framework import serializers
from .models import Produto, FamiliaProduto, Dispositivo

class FamiliaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamiliaProduto
        fields = ['id', 'nome']


class ProdutoSerializer(serializers.ModelSerializer):
    # Campos calculados ou aninhados (Read-Only)
    familia_nome = serializers.CharField(source='familia.nome', read_only=True)

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