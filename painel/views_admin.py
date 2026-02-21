import pandas as pd
from django.views import View
from django.urls import reverse_lazy
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse

from .models import Dispositivo, FamiliaProduto, Produto, Midia
from .forms import ProdutoForm, FamiliaForm, ImportarProdutosForm, DispositivoForm, MidiaForm


# --- MIXINS PARA MULTI-TENANT ---
class TenantQuerySetMixin:
    """Garante que a listagem de dados seja exclusiva da empresa do usuário logado."""
    def get_queryset(self):
        return super().get_queryset().filter(empresa=self.request.user.perfil.empresa)

class TenantFormSaveMixin:
    """Injeta a empresa do usuário logado ao salvar um novo registro."""
    def form_valid(self, form):
        form.instance.empresa = self.request.user.perfil.empresa
        return super().form_valid(form)


# --- DASHBOARD ---
@login_required
def dashboard_index(request: HttpRequest) -> HttpResponse:
    empresa_atual = request.user.perfil.empresa
    context = {
        'kpis': {
            'dispositivos_total': Dispositivo.objects.filter(empresa=empresa_atual).count(),
            'produtos_total': Produto.objects.filter(empresa=empresa_atual).count(),
            'produtos_oferta': Produto.objects.filter(empresa=empresa_atual, em_oferta=True).count(),
            'familias_total': FamiliaProduto.objects.filter(empresa=empresa_atual).count(),
        }
    }
    return render(request, 'painel/dashboard/index.html', context)


# --- MÓDULO: PRODUTOS ---
class ProdutoListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    model = Produto
    template_name = 'painel/produtos/lista.html'
    context_object_name = 'page_obj'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('familia').order_by('ordem', 'descricao')
        term = self.request.GET.get('q')
        familia_id = self.request.GET.get('familia') # Captura o novo filtro
        
        if term:
            queryset = queryset.filter(Q(descricao__icontains=term) | Q(codigo__icontains=term))
            
        if familia_id: # Aplica o filtro de família se selecionado
            queryset = queryset.filter(familia_id=familia_id)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['familia_id'] = self.request.GET.get('familia', '')
        # Envia as famílias da empresa atual para popular o Dropdown no HTML
        context['familias'] = FamiliaProduto.objects.filter(empresa=self.request.user.perfil.empresa).order_by('nome')
        context['total_count'] = self.get_queryset().count()
        return context

class ProdutoCreateView(LoginRequiredMixin, SuccessMessageMixin, TenantFormSaveMixin, CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'painel/produtos/form.html'
    success_url = reverse_lazy('produtos_list')
    success_message = "Produto criado com sucesso!"
    extra_context = {'titulo': 'Novo Produto'}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.perfil.empresa
        return kwargs

class ProdutoUpdateView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'painel/produtos/form.html'
    success_url = reverse_lazy('produtos_list')
    success_message = "Produto atualizado com sucesso!"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Editando: {self.object.descricao}"
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.perfil.empresa
        return kwargs

class ProdutoDeleteView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, DeleteView):
    model = Produto
    template_name = 'painel/produtos/confirm_delete.html'
    success_url = reverse_lazy('produtos_list')
    success_message = "Produto removido com sucesso!"

class ProdutoImportView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    template_name = 'painel/produtos/importar.html'
    form_class = ImportarProdutosForm
    success_url = reverse_lazy('produtos_list')
    success_message = "Importação concluída com sucesso!"

    COL_CODIGO = 'CÓDIGO DO PRODUTO'
    COL_DESCRICAO = 'DESCRIÇÃO DO PRODUTO'
    COL_PRECO = 'PREÇO UNITÁRIO DE VENDA'
    COL_FAMILIA = 'FAMÍLIA DE PRODUTO'

    def form_valid(self, form):
        arquivo = form.cleaned_data['arquivo_excel']
        try:
            self._processar_excel(arquivo, self.request.user.perfil.empresa)
            return super().form_valid(form)
        except Exception as e:
            form.add_error(None, f"Erro: {str(e)}")
            return self.form_invalid(form)

    def _processar_excel(self, arquivo, empresa):
        df = pd.read_excel(arquivo)
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        familias_cache = {f.nome: f for f in FamiliaProduto.objects.filter(empresa=empresa)}

        for _, row in df.iterrows():
            codigo = str(row[self.COL_CODIGO]).strip()
            descricao = str(row[self.COL_DESCRICAO]).strip()
            familia_nome = str(row[self.COL_FAMILIA]).strip().upper()
            preco = self._limpar_valor_monetario(row[self.COL_PRECO])

            if preco is None: continue

            if familia_nome not in familias_cache:
                familia_obj = FamiliaProduto.objects.create(nome=familia_nome, empresa=empresa)
                familias_cache[familia_nome] = familia_obj
            else:
                familia_obj = familias_cache[familia_nome]

            Produto.objects.update_or_create(
                codigo=codigo, empresa=empresa, # O código é único por empresa
                defaults={'descricao': descricao, 'preco': preco, 'familia': familia_obj}
            )

    @staticmethod
    def _limpar_valor_monetario(valor_raw):
        if pd.isna(valor_raw): return None
        if isinstance(valor_raw, str):
            try: return float(valor_raw.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.').strip())
            except ValueError: return None
        return float(valor_raw)
    
@login_required
@require_POST
def produto_toggle_visibilidade(request, pk):
    """Ativa ou desativa a exibição do produto via AJAX (Switch)."""
    produto = get_object_or_404(Produto, pk=pk, empresa=request.user.perfil.empresa)
    produto.exibir_no_painel = not produto.exibir_no_painel
    produto.save()
    
    return JsonResponse({
        "status": "success", 
        "exibir_no_painel": produto.exibir_no_painel
    })


# --- MÓDULO: FAMÍLIAS ---
class FamiliaListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    model = FamiliaProduto
    template_name = 'painel/familias/lista.html'
    context_object_name = 'familias'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by('nome')
        term = self.request.GET.get('q')
        if term: qs = qs.filter(nome__icontains=term)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context

class FamiliaCreateView(LoginRequiredMixin, SuccessMessageMixin, TenantFormSaveMixin, CreateView):
    model = FamiliaProduto
    form_class = FamiliaForm
    template_name = 'painel/familias/form.html'
    success_url = reverse_lazy('familia_list')
    success_message = "Família criada com sucesso!"
    extra_context = {'titulo': 'Nova Família'}

class FamiliaUpdateView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, UpdateView):
    model = FamiliaProduto
    form_class = FamiliaForm
    template_name = 'painel/familias/form.html'
    success_url = reverse_lazy('familia_list')
    success_message = "Família atualizada com sucesso!"
    extra_context = {'titulo': 'Editar Família'}

class FamiliaDeleteView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, DeleteView):
    model = FamiliaProduto
    template_name = 'painel/familias/confirm_delete.html'
    success_url = reverse_lazy('familia_list')
    success_message = "Família removida!"

@login_required
def familia_produtos_json(request, pk):
    """
    Retorna os produtos de uma família específica em formato JSON.
    Usado no Modal de auditoria dentro da página de configuração da TV.
    """
    familia = get_object_or_404(FamiliaProduto, pk=pk, empresa=request.user.perfil.empresa)
    
    # Busca os produtos respeitando a mesma ordem que aparecerão na TV
    produtos = Produto.objects.filter(familia=familia, empresa=request.user.perfil.empresa).order_by('ordem', 'descricao')
    
    dados = []
    for p in produtos:
        dados.append({
            'id': p.id,
            'descricao': p.descricao,
            'preco': str(p.preco),
            'em_oferta': p.em_oferta,
            'exibir_no_painel': p.exibir_no_painel
        })
        
    return JsonResponse({'status': 'success', 'produtos': dados})


# --- MÓDULO: DISPOSITIVOS (TVs) ---
class DispositivoContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self.request.user.perfil.empresa
        context['todas_familias'] = FamiliaProduto.objects.filter(empresa=empresa).order_by('nome')
        context['todas_midias'] = Midia.objects.filter(empresa=empresa, ativo=True).order_by('nome')
        return context

class DispositivoListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    model = Dispositivo
    template_name = 'painel/dispositivos/lista.html'
    context_object_name = 'dispositivos'
    
    def get_queryset(self):
        return super().get_queryset().order_by('-created_at')

class DispositivoCreateView(LoginRequiredMixin, SuccessMessageMixin, TenantFormSaveMixin, DispositivoContextMixin, CreateView):
    model = Dispositivo
    form_class = DispositivoForm
    template_name = 'painel/dispositivos/form.html'
    success_url = reverse_lazy('dispositivo_list')
    success_message = "Nova TV adicionada!"
    extra_context = {'titulo': 'Nova TV'}

class DispositivoUpdateView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, DispositivoContextMixin, UpdateView):
    model = Dispositivo
    form_class = DispositivoForm
    template_name = 'painel/dispositivos/form.html'
    success_url = reverse_lazy('dispositivo_list')
    success_message = "Configurações atualizadas."
    extra_context = {'titulo': 'Configurar TV'}

class DispositivoDeleteView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, DeleteView):
    model = Dispositivo
    template_name = 'painel/dispositivos/confirm_delete.html'
    success_url = reverse_lazy('dispositivo_list')
    success_message = "Dispositivo removido."

class DispositivoDesconectarView(LoginRequiredMixin, View):
    def post(self, request, pk):
        dispositivo = get_object_or_404(Dispositivo, pk=pk, empresa=request.user.perfil.empresa)
        import uuid
        from .models import gerar_codigo_curto
        
        dispositivo.uuid = uuid.uuid4()
        dispositivo.codigo_acesso = gerar_codigo_curto()
        while Dispositivo.objects.filter(codigo_acesso=dispositivo.codigo_acesso).exists():
            dispositivo.codigo_acesso = gerar_codigo_curto()
        dispositivo.save()
        
        return JsonResponse({"status": "success", "message": "TV desconectada!", "novo_codigo": dispositivo.codigo_acesso})


# --- MÓDULO: MÍDIAS ---
class MidiaListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    model = Midia
    template_name = 'painel/midias/lista.html'
    context_object_name = 'midias'
    paginate_by = 20
    
    def get_queryset(self):
        return super().get_queryset().order_by('-created_at')

class MidiaCreateView(LoginRequiredMixin, SuccessMessageMixin, TenantFormSaveMixin, CreateView):
    model = Midia
    form_class = MidiaForm
    template_name = 'painel/midias/form.html'
    success_url = reverse_lazy('midia_list')
    success_message = "Mídia enviada com sucesso!"

class MidiaUpdateView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, UpdateView):
    model = Midia
    form_class = MidiaForm
    template_name = 'painel/midias/form.html'
    success_url = reverse_lazy('midia_list')
    success_message = "Mídia atualizada."

class MidiaDeleteView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, DeleteView):
    model = Midia
    template_name = 'painel/midias/confirm_delete.html'
    success_url = reverse_lazy('midia_list')
    success_message = "Mídia removida."

