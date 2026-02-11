import pandas as pd
from django.views import View
from django.urls import reverse_lazy
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView
from django.db.models import Q, Count
from django.http import HttpRequest, HttpResponse, JsonResponse

from .models import Dispositivo, FamiliaProduto, Produto, Midia
from .forms import ProdutoForm, FamiliaForm, ImportarProdutosForm, DispositivoForm, MidiaForm


# --- DASHBOARD ---

@login_required
def dashboard_index(request: HttpRequest) -> HttpResponse:
    """
    Renderiza o Dashboard Principal com KPIs (Key Performance Indicators).
    """
    context = {
        'kpis': {
            'dispositivos_total': Dispositivo.objects.count(),
            'produtos_total': Produto.objects.count(),
            'produtos_oferta': Produto.objects.filter(em_oferta=True).count(),
            'familias_total': FamiliaProduto.objects.count(),
        }
    }
    return render(request, 'painel/dashboard/index.html', context)


# --- MÓDULO: PRODUTOS ---

class ProdutoListView(LoginRequiredMixin, ListView):
    model = Produto
    template_name = 'painel/produtos/lista.html'
    context_object_name = 'page_obj'
    paginate_by = 20

    def get_queryset(self):
        queryset = Produto.objects.select_related('familia').order_by('ordem', 'descricao')
        
        term = self.request.GET.get('q')
        if term:
            queryset = queryset.filter(
                Q(descricao__icontains=term) | 
                Q(codigo__icontains=term)
            )
        return queryset

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
        context['produto'] = self.object 
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

    # Constantes para mapeamento do Excel
    COL_CODIGO = 'CÓDIGO DO PRODUTO'
    COL_DESCRICAO = 'DESCRIÇÃO DO PRODUTO'
    COL_PRECO = 'PREÇO UNITÁRIO DE VENDA'
    COL_FAMILIA = 'FAMÍLIA DE PRODUTO'

    def form_valid(self, form):
        arquivo = form.cleaned_data['arquivo_excel']
        try:
            self._processar_excel(arquivo)
            return super().form_valid(form)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        except Exception as e:
            form.add_error(None, f"Erro inesperado ao processar arquivo: {str(e)}")
            return self.form_invalid(form)

    def _processar_excel(self, arquivo):
        """Lê o arquivo Excel e atualiza o banco de dados."""
        df = pd.read_excel(arquivo)
        df.columns = [str(c).strip().upper() for c in df.columns]

        self._validar_colunas(df)
        
        familias_cache = {f.nome: f for f in FamiliaProduto.objects.all()}

        for _, row in df.iterrows():
            self._processar_linha(row, familias_cache)

    def _validar_colunas(self, df):
        colunas_esperadas = [
            self.COL_CODIGO, self.COL_DESCRICAO, 
            self.COL_PRECO, self.COL_FAMILIA
        ]
        for col in colunas_esperadas:
            if col not in df.columns:
                raise ValueError(f"A coluna obrigatória '{col}' não foi encontrada no arquivo.")

    def _processar_linha(self, row, familias_cache):
        codigo = str(row[self.COL_CODIGO]).strip()
        descricao = str(row[self.COL_DESCRICAO]).strip()
        familia_nome = str(row[self.COL_FAMILIA]).strip().upper()
        
        preco = self._limpar_valor_monetario(row[self.COL_PRECO])
        if preco is None:
            return

        if familia_nome not in familias_cache:
            familia_obj = FamiliaProduto.objects.create(nome=familia_nome)
            familias_cache[familia_nome] = familia_obj
        else:
            familia_obj = familias_cache[familia_nome]

        Produto.objects.update_or_create(
            codigo=codigo,
            defaults={
                'descricao': descricao,
                'preco': preco,
                'familia': familia_obj
            }
        )

    @staticmethod
    def _limpar_valor_monetario(valor_raw):
        if pd.isna(valor_raw):
            return None

        if isinstance(valor_raw, str):
            limpo = valor_raw.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
            try:
                return float(limpo.strip())
            except ValueError:
                return None
        return float(valor_raw)


# --- MÓDULO: FAMÍLIAS ---

class FamiliaListView(LoginRequiredMixin, ListView):
    model = FamiliaProduto
    template_name = 'painel/familias/lista.html'
    context_object_name = 'familias'
    paginate_by = 20

    def get_queryset(self):
        queryset = FamiliaProduto.objects.all().order_by('nome')
        term = self.request.GET.get('q')
        if term:
            queryset = queryset.filter(nome__icontains=term)
        return queryset

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


# --- MÓDULO: DISPOSITIVOS (TVs) ---

class DispositivoContextMixin:
    """
    Mixin para injetar dados auxiliares necessários 
    para a interface de configuração da TV (Drag & Drop).
    """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Apenas Famílias, pois Mídias são carregadas dinamicamente
        # ou se precisar listar mídias para drag & drop, 
        # deve-se injetar Midia.objects.all() aqui futuramente.
        context['todas_familias'] = FamiliaProduto.objects.all().order_by('nome')
        
        return context


class DispositivoListView(LoginRequiredMixin, ListView):
    model = Dispositivo
    template_name = 'painel/dispositivos/lista.html'
    context_object_name = 'dispositivos'
    
    def get_queryset(self):
        return Dispositivo.objects.all().order_by('-created_at')


class DispositivoCreateView(LoginRequiredMixin, SuccessMessageMixin, DispositivoContextMixin, CreateView):
    model = Dispositivo
    form_class = DispositivoForm
    template_name = 'painel/dispositivos/form.html'
    success_url = reverse_lazy('dispositivo_list')
    success_message = "Nova TV adicionada! Use o código de pareamento para conectar."
    extra_context = {'titulo': 'Nova TV'}


class DispositivoUpdateView(LoginRequiredMixin, SuccessMessageMixin, DispositivoContextMixin, UpdateView):
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

class DispositivoDesconectarView(LoginRequiredMixin, View):
    """
    Reseta o pareamento da TV (UUID e Código) sem excluir o registro do banco.
    """
    def post(self, request, pk):
        dispositivo = get_object_or_404(Dispositivo, pk=pk)
        
        import uuid
        from .models import gerar_codigo_curto
        
        dispositivo.uuid = uuid.uuid4()
        dispositivo.codigo_acesso = gerar_codigo_curto()
        
        while Dispositivo.objects.filter(codigo_acesso=dispositivo.codigo_acesso).exists():
            dispositivo.codigo_acesso = gerar_codigo_curto()
            
        dispositivo.save()
        
        return JsonResponse({
            "status": "success", 
            "message": "TV desconectada com sucesso!",
            "novo_codigo": dispositivo.codigo_acesso
        })

# --- MÓDULO: MÍDIAS ---

class MidiaListView(LoginRequiredMixin, ListView):
    model = Midia
    template_name = 'painel/midias/lista.html'
    context_object_name = 'midias'
    paginate_by = 20
    
    def get_queryset(self):
        return Midia.objects.all().order_by('-created_at')

class MidiaCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Midia
    form_class = MidiaForm
    template_name = 'painel/midias/form.html'
    success_message = "Mídia enviada com sucesso! Configure o layout no Estúdio."
    
    def get_success_url(self):
        return reverse_lazy('estudio_editor', kwargs={'pk': self.object.id})

class MidiaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Midia
    form_class = MidiaForm
    template_name = 'painel/midias/form.html'
    success_message = "Mídia atualizada."
    
    def get_success_url(self):
        return reverse_lazy('midia_list')

class MidiaDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Midia
    template_name = 'painel/midias/confirm_delete.html'
    success_url = reverse_lazy('midia_list')
    success_message = "Mídia removida."

# View placeholder para o Estúdio
@login_required
def estudio_editor(request, pk):
    midia = get_object_or_404(Midia, pk=pk)
    return render(request, 'painel/estudio/editor.html', {'midia': midia})