import pandas as pd
from django.urls import reverse_lazy
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView
from django.db.models import Q
from .models import Dispositivo, FamiliaProduto, Produto, VideoPropaganda, VideoTemplate
from .forms import ProdutoForm, FamiliaForm, ImportarProdutosForm, DispositivoForm, VideoTemplateForm


# --- DASHBOARD (Function View) ---
@login_required
def dashboard_index(request):
    """
    Dashboard Principal com KPIs.
    """
    context = {
        'kpis': {
            'dispositivos_total': Dispositivo.objects.count(),
            'produtos_total': Produto.objects.count(),
            'produtos_oferta': Produto.objects.filter(em_oferta=True).count(),
            'propagandas_ativas': VideoPropaganda.objects.filter(ativo=True).count(),
            'templates_total': VideoTemplate.objects.count(),
            'familias_total': FamiliaProduto.objects.count(),
        }
    }
    return render(request, 'painel/dashboard/index.html', context)


# --- CRUD PRODUTOS (GENERIC VIEWS) ---

class ProdutoListView(LoginRequiredMixin, ListView):
    model = Produto
    template_name = 'painel/produtos/lista.html'
    context_object_name = 'page_obj' # Mantém compatibilidade com seu template atual
    paginate_by = 20

    def get_queryset(self):
        # Otimização com select_related e ordenação
        qs = Produto.objects.select_related('familia').order_by('ordem', 'descricao')
        
        # Lógica de Busca
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(descricao__icontains=query) | 
                Q(codigo__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['total_count'] = self.get_queryset().count()
        return context

class ProdutoCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'painel/produtos/form.html'
    success_url = reverse_lazy('produtos_list')
    success_message = "Produto criado com sucesso!"
    extra_context = {'titulo': 'Novo Produto'}

class ProdutoUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'painel/produtos/form.html'
    success_url = reverse_lazy('produtos_list')
    success_message = "Produto atualizado com sucesso!"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Editando: {self.object.descricao}"
        context['produto'] = self.object # Garante que o template receba a variável 'produto' para preview de imagem
        return context

class ProdutoDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Produto
    template_name = 'painel/produtos/confirm_delete.html'
    success_url = reverse_lazy('produtos_list')
    success_message = "Produto removido com sucesso!"

class ProdutoImportView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    template_name = 'painel/produtos/importar.html'
    form_class = ImportarProdutosForm
    success_url = reverse_lazy('produtos_list')
    success_message = "Importação concluída com sucesso!"

    def form_valid(self, form):
        arquivo = form.cleaned_data['arquivo_excel']
        try:
            self.processar_arquivo(arquivo)
            return super().form_valid(form)
        except Exception as e:
            form.add_error(None, f"Erro ao processar arquivo: {str(e)}")
            return self.form_invalid(form)

    def processar_arquivo(self, arquivo):
        # Lógica migrada do admin.py e limpa
        df = pd.read_excel(arquivo)
        df.columns = [str(c).strip().upper() for c in df.columns]

        col_codigo = 'CÓDIGO DO PRODUTO'
        col_descricao = 'DESCRIÇÃO DO PRODUTO'
        col_preco = 'PREÇO UNITÁRIO DE VENDA'
        col_familia = 'FAMÍLIA DE PRODUTO'
        
        colunas_esperadas = [col_codigo, col_descricao, col_preco, col_familia]
        
        for col in colunas_esperadas:
            if col not in df.columns:
                raise ValueError(f"Coluna obrigatória não encontrada: '{col}'")

        # Cache de famílias para evitar queries repetidas
        familias_cache = {f.nome: f for f in FamiliaProduto.objects.all()}

        for index, row in df.iterrows():
            codigo = str(row[col_codigo]).strip()
            descricao = str(row[col_descricao]).strip()
            familia_nome = str(row[col_familia]).strip().upper()
            
            valor_raw = row[col_preco]
            if pd.isna(valor_raw): continue

            if isinstance(valor_raw, str):
                valor_raw = valor_raw.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.').strip()
            
            try:
                preco = float(valor_raw)
            except ValueError:
                continue

            # Resolve a Família
            if familia_nome not in familias_cache:
                # Se não existe, cria na hora
                familia_obj = FamiliaProduto.objects.create(nome=familia_nome)
                familias_cache[familia_nome] = familia_obj
            else:
                familia_obj = familias_cache[familia_nome]

            # Update or Create Logic
            Produto.objects.update_or_create(
                codigo=codigo,
                defaults={
                    'descricao': descricao,
                    'preco': preco,
                    'familia': familia_obj
                }
            )
        
        return True


# --- CRUD FAMÍLIAS (GENERIC VIEWS) ---

class FamiliaListView(LoginRequiredMixin, ListView):
    model = FamiliaProduto
    template_name = 'painel/familias/lista.html'
    context_object_name = 'familias'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return FamiliaProduto.objects.filter(nome__icontains=query).order_by('nome')
        return FamiliaProduto.objects.all().order_by('nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context

class FamiliaCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = FamiliaProduto
    form_class = FamiliaForm
    template_name = 'painel/familias/form.html'
    success_url = reverse_lazy('familia_list')
    success_message = "Família criada com sucesso!"
    extra_context = {'titulo': 'Nova Família'}

class FamiliaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = FamiliaProduto
    form_class = FamiliaForm
    template_name = 'painel/familias/form.html'
    success_url = reverse_lazy('familia_list')
    success_message = "Família atualizada com sucesso!"
    extra_context = {'titulo': 'Editar Família'}

class FamiliaDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = FamiliaProduto
    template_name = 'painel/familias/confirm_delete.html'
    success_url = reverse_lazy('familia_list')
    success_message = "Família removida com sucesso!"

# --- CRUD DISPOSITIVOS (GENERIC VIEWS) ---

class DispositivoListView(LoginRequiredMixin, ListView):
    model = Dispositivo
    template_name = 'painel/dispositivos/lista.html'
    context_object_name = 'dispositivos'
    
    def get_queryset(self):
        return Dispositivo.objects.all().order_by('-created_at')

class DispositivoCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Dispositivo
    form_class = DispositivoForm
    template_name = 'painel/dispositivos/form.html'
    success_url = reverse_lazy('dispositivo_list')
    success_message = "Nova TV adicionada! Use o código de pareamento para conectar."
    extra_context = {'titulo': 'Nova TV'}

class DispositivoUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Dispositivo
    form_class = DispositivoForm
    template_name = 'painel/dispositivos/form.html'
    success_url = reverse_lazy('dispositivo_list')
    success_message = "Configurações da TV atualizadas."
    extra_context = {'titulo': 'Configurar TV'}

class DispositivoDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Dispositivo
    template_name = 'painel/dispositivos/confirm_delete.html'
    success_url = reverse_lazy('dispositivo_list')
    success_message = "Dispositivo removido."


# --- CRUD TEMPLATES ---

class TemplateListView(LoginRequiredMixin, ListView):
    model = VideoTemplate
    template_name = 'painel/templates/lista.html'
    context_object_name = 'templates'
    
    def get_queryset(self):
        return VideoTemplate.objects.all().order_by('-id')

class TemplateCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = VideoTemplate
    form_class = VideoTemplateForm
    template_name = 'painel/templates/form.html'
    success_url = reverse_lazy('template_list')
    success_message = "Template criado! Agora abra o Editor Visual para ajustar."
    extra_context = {'titulo': 'Novo Template'}

class TemplateUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = VideoTemplate
    form_class = VideoTemplateForm
    template_name = 'painel/templates/form.html'
    success_url = reverse_lazy('template_list')
    success_message = "Dados do template atualizados."
    extra_context = {'titulo': 'Editar Dados do Template'}

class TemplateDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = VideoTemplate
    template_name = 'painel/templates/confirm_delete.html'
    success_url = reverse_lazy('template_list')
    success_message = "Template removido com sucesso!"