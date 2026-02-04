from django import forms
from .models import Produto, FamiliaProduto, Dispositivo, VideoTemplate

class ImportarProdutosForm(forms.Form):
    arquivo_excel = forms.FileField(label='Selecione o arquivo Excel (.xlsx)')
    
    def clean_arquivo_excel(self):
        arquivo = self.cleaned_data.get('arquivo_excel')
        if not arquivo.name.endswith('.xlsx'):
            raise forms.ValidationError("O arquivo deve ser um Excel (.xlsx)")
        return 
    
class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['codigo', 'descricao', 'preco', 'familia', 'imagem', 'em_oferta', 'exibir_no_painel']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm',
                'placeholder': 'Ex: 78910...'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm',
                'placeholder': 'Nome do produto'
            }),
            'preco': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm',
                'step': '0.01'
            }),
            'familia': forms.Select(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm'
            }),
            'imagem': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'
            }),
            # Checkboxes ganham uma classe para serem estilizados como "Switches" no CSS ou manter padrão limpo
            'em_oferta': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded'}),
            'exibir_no_painel': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded'}),
        }

class FamiliaForm(forms.ModelForm):
    class Meta:
        model = FamiliaProduto
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm',
                'placeholder': 'Ex: Açougue, Bebidas, Padaria...'
            }),
        }

class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        fields = ['nome', 'orientacao', 'modo_exibicao', 'exibir_apenas_familias', 'exibir_propagandas']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm',
                'placeholder': 'Ex: TV da Entrada, TV do Açougue...'
            }),
            'orientacao': forms.Select(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm'
            }),
            'modo_exibicao': forms.Select(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm'
            }),
            'exibir_apenas_familias': forms.SelectMultiple(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm min-h-[100px]'
            }),
            'exibir_propagandas': forms.SelectMultiple(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm min-h-[100px]'
            }),
        }

class VideoTemplateForm(forms.ModelForm):
    class Meta:
        model = VideoTemplate
        fields = ['nome', 'duracao', 'arquivo_video']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm',
                'placeholder': 'Ex: Ofertas de Fim de Semana'
            }),
            'duracao': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 shadow-sm text-sm',
                'placeholder': '15'
            }),
            'arquivo_video': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100'
            }),
        }