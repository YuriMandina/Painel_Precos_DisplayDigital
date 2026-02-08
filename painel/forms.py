from django import forms
from .models import Produto, FamiliaProduto, Dispositivo, VideoTemplate

# --- Constantes de Estilo (Tailwind CSS) ---
# Centraliza o design para facilitar manutenção e reduzir repetição
CSS_INPUT = (
    'w-full rounded-lg border-gray-300 focus:border-indigo-500 '
    'focus:ring-indigo-500 shadow-sm text-sm'
)

CSS_CHECKBOX = (
    'h-4 w-4 text-indigo-600 focus:ring-indigo-500 '
    'border-gray-300 rounded'
)

CSS_FILE_BASE = (
    'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 '
    'file:rounded-full file:border-0 file:text-xs file:font-semibold'
)

CSS_FILE_INDIGO = f"{CSS_FILE_BASE} file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
CSS_FILE_PURPLE = f"{CSS_FILE_BASE} file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"


class ImportarProdutosForm(forms.Form):
    """Formulário simples para upload de planilhas Excel."""
    arquivo_excel = forms.FileField(label='Selecione o arquivo Excel (.xlsx)')
    
    def clean_arquivo_excel(self):
        arquivo = self.cleaned_data.get('arquivo_excel')
        if arquivo and not arquivo.name.endswith('.xlsx'):
            raise forms.ValidationError("O arquivo deve ser um Excel (.xlsx)")
        return arquivo


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            'codigo', 'descricao', 'preco', 'familia', 
            'imagem', 'em_oferta', 'exibir_no_painel'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': CSS_INPUT,
                'placeholder': 'Ex: 78910...'
            }),
            'descricao': forms.TextInput(attrs={
                'class': CSS_INPUT,
                'placeholder': 'Nome do produto'
            }),
            'preco': forms.NumberInput(attrs={
                'class': CSS_INPUT,
                'step': '0.01'
            }),
            'familia': forms.Select(attrs={
                'class': CSS_INPUT
            }),
            'imagem': forms.FileInput(attrs={
                'class': CSS_FILE_INDIGO
            }),
            'em_oferta': forms.CheckboxInput(attrs={'class': CSS_CHECKBOX}),
            'exibir_no_painel': forms.CheckboxInput(attrs={'class': CSS_CHECKBOX}),
        }


class FamiliaForm(forms.ModelForm):
    class Meta:
        model = FamiliaProduto
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': CSS_INPUT,
                'placeholder': 'Ex: Açougue, Bebidas, Padaria...'
            }),
        }


class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        fields = ['nome', 'orientacao', 'playlist'] 
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': CSS_INPUT,
                'placeholder': 'Ex: TV do Açougue (Apenas Identificação)'
            }),
            'orientacao': forms.Select(attrs={
                'class': CSS_INPUT
            }),
            'playlist': forms.HiddenInput()
        }


class VideoTemplateForm(forms.ModelForm):
    class Meta:
        model = VideoTemplate
        fields = ['nome', 'duracao', 'arquivo_video']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': CSS_INPUT,
                'placeholder': 'Ex: Ofertas de Fim de Semana'
            }),
            'duracao': forms.NumberInput(attrs={
                'class': CSS_INPUT,
                'placeholder': '15'
            }),
            'arquivo_video': forms.FileInput(attrs={
                'class': CSS_FILE_PURPLE
            }),
        }