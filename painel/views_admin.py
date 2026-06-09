# ==============================================================================
#                                  IMPORTS
# ==============================================================================
from pyexpat.errors import messages
import uuid
from typing import Any, Dict, Optional

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView, 
    DeleteView, 
    FormView, 
    ListView, 
    UpdateView
)

from .forms import (
    DispositivoForm, 
    FamiliaForm, 
    ImportarProdutosForm, 
    MidiaForm, 
    ProdutoForm
)
from .models import (
    Dispositivo, 
    FamiliaProduto, 
    Midia,
    Perfil, 
    Produto,
    Convite,
    gerar_codigo_curto
)
from .forms import (
    DispositivoForm, 
    FamiliaForm, 
    ImportarProdutosForm, 
    MidiaForm, 
    ProdutoForm,
    ConviteEmailForm
)
from django.core.mail import send_mail
from django.conf import settings

# ==============================================================================
#                          MIXINS: ISOLAMENTO TENANT
# ==============================================================================

class TenantQuerySetMixin:
    """
    Sobrescreve a recuperação de QuerySets para garantir que os registros 
    retornados pertençam exclusivamente à empresa (Tenant) do usuário autenticado.
    """
    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(empresa=self.request.user.perfil.empresa)


class TenantFormSaveMixin:
    """
    Intercepta o salvamento de formulários para injetar automaticamente 
    a empresa (Tenant) do usuário autenticado na instância do modelo.
    """
    def form_valid(self, form: Any) -> HttpResponse:
        form.instance.empresa = self.request.user.perfil.empresa
        return super().form_valid(form)
    

class EquipeListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    model = Perfil
    template_name = 'painel/equipe/lista.html'
    context_object_name = 'membros'

    def dispatch(self, request, *args, **kwargs):
        # Proteção extra: Apenas admins da empresa podem acessar essa tela
        if not request.user.perfil.is_admin:
            messages.error(request, "Acesso restrito: Apenas administradores podem gerenciar a equipe.")
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Retorna todos da mesma empresa, exceto o próprio usuário logado
        return super().get_queryset().exclude(usuario=self.request.user).order_by('status', 'usuario__first_name')
        
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['convites'] = Convite.objects.filter(
            empresa=self.request.user.perfil.empresa, 
            status=Convite.Status.PENDENTE
        ).order_by('-created_at')
        context['convite_form'] = ConviteEmailForm()
        return context


class EquipeConvidarView(LoginRequiredMixin, FormView):
    template_name = 'painel/equipe/lista.html'
    form_class = ConviteEmailForm
    success_url = reverse_lazy('equipe_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.perfil.is_admin:
            messages.error(request, "Acesso restrito.")
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: ConviteEmailForm) -> HttpResponse:
        email = form.cleaned_data['email']
        empresa = self.request.user.perfil.empresa
        
        # Evitar convites duplicados
        if Convite.objects.filter(empresa=empresa, email=email, status=Convite.Status.PENDENTE).exists():
            messages.warning(self.request, f"Um convite já está pendente para {email}.")
            return redirect(self.success_url)

        convite = Convite.objects.create(empresa=empresa, email=email)
        
        # Enviar E-mail
        link = self.request.build_absolute_uri(reverse_lazy('aceitar_convite', kwargs={'token': convite.token}))
        assunto = f"Convite para acessar {empresa.nome} no DisplayDigital"
        mensagem = f"Olá!\n\nVocê foi convidado para acessar o painel administrativo de {empresa.nome}.\n\nClique no link abaixo para criar sua senha e acessar:\n{link}\n\nBem-vindo à equipe!"
        
        try:
            send_mail(
                subject=assunto,
                message=mensagem,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(self.request, f"Convite enviado com sucesso para {email}!")
        except Exception as e:
            convite.delete()
            messages.error(self.request, f"Falha ao enviar e-mail: {str(e)}")
            
        return super().form_valid(form)
    
    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, error)
        return redirect(self.success_url)


# ==============================================================================
#                                DASHBOARD
# ==============================================================================

@login_required
def dashboard_index(request: HttpRequest) -> HttpResponse:
    """
    Renderiza a visão geral do painel administrativo, compilando os KPIs 
    principais referentes à empresa do usuário logado.
    """
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


# ==============================================================================
#                           MÓDULO: PRODUTOS
# ==============================================================================

class ProdutoListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    model = Produto
    template_name = 'painel/produtos/lista.html'
    context_object_name = 'page_obj'
    paginate_by = 20

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset().select_related('familia').order_by('ordem', 'descricao')
        term = self.request.GET.get('q')
        familia_id = self.request.GET.get('familia')
        
        if term:
            queryset = queryset.filter(Q(descricao__icontains=term) | Q(codigo__icontains=term))
            
        if familia_id:
            queryset = queryset.filter(familia_id=familia_id)
            
        return queryset

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['familia_id'] = self.request.GET.get('familia', '')
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

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.perfil.empresa
        return kwargs


class ProdutoUpdateView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'painel/produtos/form.html'
    success_url = reverse_lazy('produtos_list')
    success_message = "Produto atualizado com sucesso!"
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Editando: {self.object.descricao}"
        return context

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.perfil.empresa
        return kwargs


class ProdutoDeleteView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, DeleteView):
    model = Produto
    template_name = 'painel/produtos/confirm_delete.html'
    success_url = reverse_lazy('produtos_list')
    success_message = "Produto removido com sucesso!"


class ProdutoImportView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    """
    Processa o upload de arquivos Excel para criação ou atualização em massa (Upsert)
    de instâncias de Produto e FamiliaProduto no banco de dados.
    """
    template_name = 'painel/produtos/importar.html'
    form_class = ImportarProdutosForm
    success_url = reverse_lazy('produtos_list')
    success_message = "Importação concluída com sucesso!"

    COL_CODIGO = 'CÓDIGO DO PRODUTO'
    COL_DESCRICAO = 'DESCRIÇÃO DO PRODUTO'
    COL_PRECO = 'PREÇO UNITÁRIO DE VENDA'
    COL_FAMILIA = 'FAMÍLIA DE PRODUTO'

    def form_valid(self, form: ImportarProdutosForm) -> HttpResponse:
        arquivo = form.cleaned_data['arquivo_excel']
        try:
            self._processar_excel(arquivo, self.request.user.perfil.empresa)
            return super().form_valid(form)
        except Exception as e:
            form.add_error(None, f"Erro no processamento do arquivo: {str(e)}")
            return self.form_invalid(form)

    def _processar_excel(self, arquivo: Any, empresa: Any) -> None:
        """Extrai, limpa e persiste os dados do DataFrame."""
        df = pd.read_excel(arquivo)
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        familias_cache = {f.nome: f for f in FamiliaProduto.objects.filter(empresa=empresa)}

        for _, row in df.iterrows():
            codigo = str(row[self.COL_CODIGO]).strip()
            descricao = str(row[self.COL_DESCRICAO]).strip()
            familia_nome = str(row[self.COL_FAMILIA]).strip().upper()
            preco = self._limpar_valor_monetario(row[self.COL_PRECO])

            if preco is None: 
                continue

            if familia_nome not in familias_cache:
                familia_obj = FamiliaProduto.objects.create(nome=familia_nome, empresa=empresa)
                familias_cache[familia_nome] = familia_obj
            else:
                familia_obj = familias_cache[familia_nome]

            Produto.objects.update_or_create(
                codigo=codigo, 
                empresa=empresa,
                defaults={'descricao': descricao, 'preco': preco, 'familia': familia_obj}
            )

    @staticmethod
    def _limpar_valor_monetario(valor_raw: Any) -> Optional[float]:
        """Sanitiza strings monetárias para conversão em float."""
        if pd.isna(valor_raw): 
            return None
        if isinstance(valor_raw, str):
            try: 
                return float(valor_raw.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.').strip())
            except ValueError: 
                return None
        return float(valor_raw)


@login_required
@require_POST
def produto_toggle_visibilidade(request: HttpRequest, pk: int) -> JsonResponse:
    """Inverte o status booleano do campo 'exibir_no_painel' do produto (Endpoint AJAX)."""
    produto = get_object_or_404(Produto, pk=pk, empresa=request.user.perfil.empresa)
    produto.exibir_no_painel = not produto.exibir_no_painel
    produto.save(update_fields=['exibir_no_painel'])
    
    return JsonResponse({
        "status": "success", 
        "exibir_no_painel": produto.exibir_no_painel
    })


# ==============================================================================
#                        MÓDULO: FAMÍLIAS DE PRODUTOS
# ==============================================================================

class FamiliaListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    model = FamiliaProduto
    template_name = 'painel/familias/lista.html'
    context_object_name = 'familias'
    paginate_by = 20

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset().order_by('nome')
        term = self.request.GET.get('q')
        if term: 
            qs = qs.filter(nome__icontains=term)
        return qs

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
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
def familia_produtos_json(request: HttpRequest, pk: int) -> JsonResponse:
    """
    Payload JSON contendo a estrutura de produtos de uma família específica.
    Utilizado para popular modais de auditoria no front-end de configuração.
    """
    familia = get_object_or_404(FamiliaProduto, pk=pk, empresa=request.user.perfil.empresa)
    produtos = Produto.objects.filter(
        familia=familia, 
        empresa=request.user.perfil.empresa
    ).order_by('ordem', 'descricao')
    
    dados = [
        {
            'id': p.id,
            'descricao': p.descricao,
            'preco': str(p.preco),
            'em_oferta': p.em_oferta,
            'exibir_no_painel': p.exibir_no_painel
        } for p in produtos
    ]
        
    return JsonResponse({'status': 'success', 'produtos': dados})


# ==============================================================================
#                        MÓDULO: DISPOSITIVOS (TVs)
# ==============================================================================

class DispositivoContextMixin:
    """Injeta listas auxiliares (Famílias e Mídias) no contexto do formulário."""
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        empresa = self.request.user.perfil.empresa
        context['todas_familias'] = FamiliaProduto.objects.filter(empresa=empresa).order_by('nome')
        context['todas_midias'] = Midia.objects.filter(empresa=empresa, ativo=True).order_by('nome')
        return context


class DispositivoListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    model = Dispositivo
    template_name = 'painel/dispositivos/lista.html'
    context_object_name = 'dispositivos'
    
    def get_queryset(self) -> QuerySet:
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
    """
    Invalida a sessão atual de um dispositivo redefinindo seus tokens de acesso 
    (UUID e Código Curto). Exige repareamento físico.
    """
    def post(self, request: HttpRequest, pk: int) -> JsonResponse:
        dispositivo = get_object_or_404(Dispositivo, pk=pk, empresa=request.user.perfil.empresa)
        
        dispositivo.uuid = uuid.uuid4()
        dispositivo.codigo_acesso = gerar_codigo_curto()
        
        # Garante unicidade absoluta do código de pareamento
        while Dispositivo.objects.filter(codigo_acesso=dispositivo.codigo_acesso).exists():
            dispositivo.codigo_acesso = gerar_codigo_curto()
            
        dispositivo.save(update_fields=['uuid', 'codigo_acesso'])
        
        return JsonResponse({
            "status": "success", 
            "message": "TV desconectada!", 
            "novo_codigo": dispositivo.codigo_acesso
        })


# ==============================================================================
#                             MÓDULO: MÍDIAS
# ==============================================================================

class MidiaListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    model = Midia
    template_name = 'painel/midias/lista.html'
    context_object_name = 'midias'
    paginate_by = 20
    
    def get_queryset(self) -> QuerySet:
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