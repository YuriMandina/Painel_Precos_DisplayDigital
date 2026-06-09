# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
from typing import Any, Dict

from django import forms

from .models import Dispositivo, FamiliaProduto, Midia, Produto

from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm


# ==============================================================================
#                             CONSTANTES DE ESTILIZAÇÃO
# ==============================================================================

CSS_INPUT = (
    'w-full rounded-xl border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 '
    'focus:ring-indigo-600 focus:border-transparent shadow-sm text-sm transition-all px-4 py-3'
)

CSS_CHECKBOX = (
    'h-5 w-5 text-indigo-600 focus:ring-indigo-500 '
    'border-slate-300 rounded shadow-sm transition-colors cursor-pointer'
)

CSS_FILE_BASE = (
    'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 '
    'file:rounded-full file:border-0 file:text-xs file:font-bold transition-all'
)

CSS_FILE_INDIGO = f"{CSS_FILE_BASE} file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"


# ==============================================================================
#                                  FORMULÁRIOS
# ==============================================================================

class ImportarProdutosForm(forms.Form):
    """Formulário para upload de payload Excel contendo carga em massa de produtos."""
    
    arquivo_excel = forms.FileField(
        label='Selecione o arquivo Excel (.xlsx)',
        widget=forms.FileInput(attrs={'class': CSS_FILE_INDIGO})
    )
    
    def clean_arquivo_excel(self) -> Any:
        """Validação de extensão MIME no nível da aplicação."""
        arquivo = self.cleaned_data.get('arquivo_excel')
        if arquivo and not arquivo.name.endswith('.xlsx'):
            raise forms.ValidationError("Formato inválido. O arquivo deve ter a extensão .xlsx.")
        return arquivo


class ProdutoForm(forms.ModelForm):
    """
    Formulário principal de Produtos. 
    Aplica restrição de QuerySet para garantir que as Famílias disponíveis
    pertençam exclusivamente ao escopo da Empresa (Tenant) do usuário.
    """
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
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
    """Formulário para manipulação de categorias/famílias de produtos."""
    class Meta:
        model = FamiliaProduto
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': CSS_INPUT, 'placeholder': 'Ex: Açougue, Bebidas...'}),
        }


class DispositivoForm(forms.ModelForm):
    """Formulário de parametrização de endpoints físicos de exibição."""
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
    """Formulário de upload e gestão de ativos de mídia estática."""
    class Meta:
        model = Midia
        fields = ['nome', 'arquivo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': CSS_INPUT, 'placeholder': 'Ex: Promoção de Natal'}),
            'arquivo': forms.FileInput(attrs={'class': 'hidden', 'accept': 'video/*,image/*'})
        }

    def clean_arquivo(self) -> Any:
        """
        Intercepta o arquivo antes de enviá-lo para a nuvem.
        Encurta o nome original do arquivo para garantir que a string devolvida 
        pelo Cloudinary não ultrapasse o limite de 100 caracteres do banco de dados (DataError).
        """
        arquivo = self.cleaned_data.get('arquivo')
        if arquivo:
            nome_base, extensao = os.path.splitext(arquivo.name)
            # Limita o nome original a apenas 20 caracteres
            nome_curto = nome_base[:20].strip()
            arquivo.name = f"{nome_curto}{extensao}"
        return arquivo
    
class RegistroForm(forms.Form):
    premium_input_css = 'block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600 focus:border-transparent sm:text-sm transition-colors'
    
    nome = forms.CharField(widget=forms.TextInput(attrs={'class': premium_input_css, 'placeholder': 'Seu nome completo'}))
    
    # O username foi removido para usar apenas email

    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': premium_input_css, 'placeholder': 'seu@email.com'}))
    
    # Adicionamos a confirmação de senha
    senha = forms.CharField(widget=forms.PasswordInput(attrs={'class': premium_input_css, 'placeholder': 'Crie uma senha segura'}))
    senha_confirmacao = forms.CharField(widget=forms.PasswordInput(attrs={'class': premium_input_css, 'placeholder': 'Confirme sua senha'}))
    
    nome_empresa = forms.CharField(
        max_length=150, 
        required=True, 
        help_text="Obrigatório para criarmos seu espaço de trabalho.",
        widget=forms.TextInput(attrs={'class': premium_input_css, 'placeholder': 'Razão Social ou Nome Fantasia'})
    )


    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este e-mail já está em uso por outra conta.")
        return email

    def clean(self):
        """Validação cruzada para garantir que as senhas batem."""
        cleaned_data = super().clean()
        senha = cleaned_data.get("senha")
        senha_confirmacao = cleaned_data.get("senha_confirmacao")
        
        if senha and senha_confirmacao and senha != senha_confirmacao:
            self.add_error('senha_confirmacao', "As senhas não coincidem. Digite novamente.")
            
        return cleaned_data

class ConviteEmailForm(forms.Form):
    """
    Formulário para o Admin convidar um novo membro via e-mail.
    """
    email = forms.EmailField(
        label="E-mail do novo membro",
        widget=forms.EmailInput(attrs={
            'class': 'block w-full pl-4 pr-3 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-600 focus:border-transparent text-sm transition-colors',
            'placeholder': 'colega@empresa.com'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este e-mail já possui uma conta no sistema.")
        return email

class AceiteConviteForm(forms.Form):
    """
    Formulário para o Convidado preencher seus dados (Nome e Senha) ao aceitar o convite.
    """
    premium_input_css = 'block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600 focus:border-transparent sm:text-sm transition-colors'
    
    nome = forms.CharField(widget=forms.TextInput(attrs={'class': premium_input_css, 'placeholder': 'Seu nome completo'}))
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': premium_input_css, 'readonly': 'readonly', 'style': 'background-color: #f3f4f6;'})
    )
    
    senha = forms.CharField(widget=forms.PasswordInput(attrs={'class': premium_input_css, 'placeholder': 'Crie uma senha segura'}))
    senha_confirmacao = forms.CharField(widget=forms.PasswordInput(attrs={'class': premium_input_css, 'placeholder': 'Confirme sua senha'}))

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get("senha")
        senha_confirmacao = cleaned_data.get("senha_confirmacao")
        
        if senha and senha_confirmacao and senha != senha_confirmacao:
            self.add_error('senha_confirmacao', "As senhas não coincidem. Digite novamente.")
            
        return cleaned_data

class EmailLoginForm(AuthenticationForm):
    """
    Substitui o formulário padrão de login para usar Email em vez de Username.
    """
    username = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={
            'class': 'block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600 focus:border-transparent sm:text-sm transition-colors',
            'placeholder': 'seu@email.com',
            'id': 'id_username',
            'required': True
        })
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600 focus:border-transparent sm:text-sm transition-colors',
            'placeholder': '••••••••',
            'id': 'id_password',
            'required': True
        })
    )