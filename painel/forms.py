from django import forms
from .models import Produto, FamiliaProduto, Dispositivo, Midia

# --- Constantes de Estilo (Tailwind CSS) ---
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


class ImportarProdutosForm(forms.Form):
    arquivo_excel = forms.FileField(
        label='Selecione o arquivo Excel (.xlsx)',
        widget=forms.FileInput(attrs={'class': CSS_FILE_INDIGO})
    )
    
    def clean_arquivo_excel(self):
        arquivo = self.cleaned_data.get('arquivo_excel')
        if arquivo and not arquivo.name.endswith('.xlsx'):
            raise forms.ValidationError("O arquivo deve ser um Excel (.xlsx)")
        return arquivo


class ProdutoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Captura a empresa passada pela View antes de iniciar o form
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        # Filtra as famílias para mostrar apenas as da empresa do usuário logado
        if self.empresa:
            self.fields['familia'].queryset = FamiliaProduto.objects.filter(empresa=self.empresa)

    class Meta:
        model = Produto
        fields = [
            'codigo', 'descricao', 'preco', 'familia', 
            'imagem', 'em_oferta', 'exibir_no_painel'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': CSS_INPUT, 'placeholder': 'Ex: 78910...'}),
            'descricao': forms.TextInput(attrs={'class': CSS_INPUT, 'placeholder': 'Nome do produto'}),
            'preco': forms.NumberInput(attrs={'class': CSS_INPUT, 'step': '0.01'}),
            'familia': forms.Select(attrs={'class': CSS_INPUT}),
            'imagem': forms.FileInput(attrs={'class': CSS_FILE_INDIGO}),
            'em_oferta': forms.CheckboxInput(attrs={'class': CSS_CHECKBOX}),
            'exibir_no_painel': forms.CheckboxInput(attrs={'class': CSS_CHECKBOX}),
        }


class FamiliaForm(forms.ModelForm):
    class Meta:
        model = FamiliaProduto
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': CSS_INPUT, 'placeholder': 'Ex: Açougue, Bebidas...'}),
        }


class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        fields = ['nome', 'titulo_exibicao', 'orientacao', 'playlist'] 
        widgets = {
            'nome': forms.TextInput(attrs={'class': CSS_INPUT, 'placeholder': 'Ex: TV do Açougue'}),
            'titulo_exibicao': forms.TextInput(attrs={'class': CSS_INPUT, 'placeholder': 'Opcional'}),
            'orientacao': forms.Select(attrs={'class': CSS_INPUT}),
            'playlist': forms.HiddenInput()
        }


class MidiaForm(forms.ModelForm):
    class Meta:
        model = Midia
        fields = ['nome', 'arquivo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': CSS_INPUT, 'placeholder': 'Ex: Promoção de Natal'}),
            'arquivo': forms.FileInput(attrs={'class': 'hidden', 'accept': 'video/*,image/*'})
        }