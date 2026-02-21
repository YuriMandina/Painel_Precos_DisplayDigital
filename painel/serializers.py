# ==============================================================================
#                                  IMPORTS
# ==============================================================================
from rest_framework import serializers
from .models import Produto, FamiliaProduto, Dispositivo


# ==============================================================================
#                                SERIALIZERS
# ==============================================================================

class FamiliaSerializer(serializers.ModelSerializer):
    """Serializer para representação de Famílias de Produtos."""
    
    class Meta:
        model = FamiliaProduto
        fields = ['id', 'nome']


class ProdutoSerializer(serializers.ModelSerializer):
    """
    Serializer principal de Produtos. 
    Expõe o id da família relacional e a string associada (familia_nome) 
    como campo read-only para facilitar o consumo via UI.
    """
    familia_nome = serializers.CharField(source='familia.nome', read_only=True)

    class Meta:
        model = Produto
        fields = [
            'id',
            'codigo',
            'descricao',
            'preco',
            'familia',       
            'familia_nome',  
            'imagem',
            'em_oferta',
            'ordem'
        ]


class DispositivoConfigSerializer(serializers.ModelSerializer):
    """
    Serializer de carga inicial para configuração do endpoint de exibição (TV).
    Transmite parâmetros operacionais como identidade (UUID), layout (orientação) 
    e regras de renderização (modo_exibicao).
    """
    
    class Meta:
        model = Dispositivo
        fields = [
            'nome',
            'modo_exibicao',
            'uuid',
            'orientacao'
        ]