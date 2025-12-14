from django import forms

class ImportarProdutosForm(forms.Form):
    arquivo_excel = forms.FileField(label='Selecione o arquivo Excel (.xlsx)')
    
    def clean_arquivo_excel(self):
        arquivo = self.cleaned_data.get('arquivo_excel')
        if not arquivo.name.endswith('.xlsx'):
            raise forms.ValidationError("O arquivo deve ser um Excel (.xlsx)")
        return arquivo