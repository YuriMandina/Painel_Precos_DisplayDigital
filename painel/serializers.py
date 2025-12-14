from rest_framework import serializers
from .models import Produto, FamiliaProduto, VideoTemplate, Dispositivo

class FamiliaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamiliaProduto
        fields = ['id', 'nome']

class VideoTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoTemplate
        fields = '__all__' # Envia tudo: video url, coordenadas top/left, cores, etc.

class ProdutoSerializer(serializers.ModelSerializer):
    # Serializamos a família para enviar o nome dela, não só o ID
    familia_nome = serializers.CharField(source='familia.nome', read_only=True)
    
    # Se o produto tiver um template de vídeo específico, enviamos os dados dele junto
    template_video = VideoTemplateSerializer(read_only=True)

    class Meta:
        model = Produto
        fields = [
            'codigo', 'descricao', 'preco', 
            'familia_nome', 'imagem', 
            'em_oferta', 'template_video'
        ]

class DispositivoConfigSerializer(serializers.ModelSerializer):
    """
    Este é o serializer que a TV vai receber.
    Ele diz qual o modo de operação e pode incluir dados extras.
    """
    class Meta:
        model = Dispositivo
        fields = ['nome', 'modo_exibicao', 'uuid']