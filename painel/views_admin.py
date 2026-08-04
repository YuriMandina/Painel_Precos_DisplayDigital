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
    SincronizacaoOmie,
    ProdutoIgnoradoOmie,
    FamiliaIgnoradaOmie,
    Empresa,
    gerar_codigo_curto
)
import json
from .services.omie_service import OmieService
from .forms import (
    DispositivoForm, 
    FamiliaForm, 
    ImportarProdutosForm, 
    MidiaForm, 
    ProdutoForm,
    ConviteEmailForm,
    IntegracoesForm
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
        
        # Evitar convites duplicados e permitir reenvio
        convite_existente = Convite.objects.filter(empresa=empresa, email=email, status=Convite.Status.PENDENTE).first()
        if convite_existente:
            convite_existente.delete()
            messages.info(self.request, f"Reenviando convite para {email}.")

        convite = Convite.objects.create(empresa=empresa, email=email)
        
        # Enviar E-mail
        link = self.request.build_absolute_uri(reverse_lazy('aceitar_convite', kwargs={'token': convite.token}))
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        
        assunto = f"Convite para acessar {empresa.nome} no DisplayDigital"
        html_message = render_to_string('painel/emails/convite.html', {'empresa': empresa, 'link': link})
        mensagem = strip_tags(html_message)
        
        try:
            send_mail(
                subject=assunto,
                message=mensagem,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
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

@login_required
@require_POST
def equipe_toggle_status_view(request: HttpRequest, pk: int) -> JsonResponse:
    """Inverte o status de ativação (is_active) de um membro da equipe via AJAX."""
    if not request.user.perfil.is_admin:
        return JsonResponse({"status": "error", "message": "Acesso negado."}, status=403)
        
    perfil = get_object_or_404(Perfil, pk=pk, empresa=request.user.perfil.empresa)
    
    # Previne que o admin desative a si próprio
    if perfil.usuario == request.user:
        return JsonResponse({"status": "error", "message": "Não é possível desativar a si próprio."}, status=400)

    # Inverte o status is_active do User do Django
    usuario = perfil.usuario
    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=['is_active'])
    
    return JsonResponse({
        "status": "success",
        "is_active": usuario.is_active
    })

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
#                        MÓDULO: LISTAS PERSONALIZADAS
# ==============================================================================

from .models import ListaPersonalizada, ListaProduto
from .forms import ListaPersonalizadaForm
import json

class ListaPersonalizadaListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    model = ListaPersonalizada
    template_name = 'painel/listas/lista.html'
    context_object_name = 'listas'

class ListaPersonalizadaCreateView(LoginRequiredMixin, SuccessMessageMixin, TenantFormSaveMixin, CreateView):
    model = ListaPersonalizada
    form_class = ListaPersonalizadaForm
    template_name = 'painel/listas/form.html'
    success_url = reverse_lazy('lista_personalizada_list')
    success_message = "Lista Personalizada criada com sucesso!"
    extra_context = {'titulo': 'Nova Lista Personalizada'}

class ListaPersonalizadaUpdateView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, UpdateView):
    model = ListaPersonalizada
    form_class = ListaPersonalizadaForm
    template_name = 'painel/listas/form.html'
    success_url = reverse_lazy('lista_personalizada_list')
    success_message = "Lista Personalizada atualizada com sucesso!"
    extra_context = {'titulo': 'Editar Lista Personalizada'}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self.request.user.perfil.empresa
        # Todos os produtos disponíveis para adicionar à lista
        context['todos_produtos'] = Produto.objects.filter(empresa=empresa).order_by('familia__nome', 'descricao')
        # Itens já presentes na lista, ordenados
        context['itens_lista'] = self.object.itens.all().select_related('produto').order_by('ordem')
        return context

class ListaPersonalizadaDeleteView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, DeleteView):
    model = ListaPersonalizada
    template_name = 'painel/listas/confirm_delete.html'
    success_url = reverse_lazy('lista_personalizada_list')
    success_message = "Lista Personalizada removida!"

@login_required
@require_POST
def lista_personalizada_update_items(request: HttpRequest, pk: int) -> JsonResponse:
    """Endpoint AJAX para salvar a ordenação e os itens de uma lista personalizada."""
    lista = get_object_or_404(ListaPersonalizada, pk=pk, empresa=request.user.perfil.empresa)
    
    try:
        data = json.loads(request.body)
        produtos_ids = data.get('produtos', [])
        
        # Deletar itens antigos
        lista.itens.all().delete()
        
        # Criar os novos itens com a ordem enviada pelo frontend
        novos_itens = []
        for index, prod_id in enumerate(produtos_ids):
            novos_itens.append(ListaProduto(
                lista=lista,
                produto_id=prod_id,
                ordem=index
            ))
            
        ListaProduto.objects.bulk_create(novos_itens)
        
        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ==============================================================================
#                        MÓDULO: DISPOSITIVOS (TVs)
# ==============================================================================

class DispositivoContextMixin:
    """Injeta listas auxiliares (Famílias, Mídias e Listas Personalizadas) no contexto do formulário."""
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        empresa = self.request.user.perfil.empresa
        context['todas_familias'] = FamiliaProduto.objects.filter(empresa=empresa).order_by('nome')
        context['todas_midias'] = Midia.objects.filter(empresa=empresa, ativo=True).order_by('nome')
        context['todas_listas'] = ListaPersonalizada.objects.filter(empresa=empresa).order_by('nome')
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



class MidiaDeleteView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, DeleteView):
    model = Midia
    template_name = 'painel/midias/confirm_delete.html'
    success_url = reverse_lazy('midia_list')
    success_message = "Mídia removida."


# ==============================================================================
#                          INTEGRAÇÃO OMIE
# ==============================================================================

@login_required
def omie_sincronizar_view(request: HttpRequest) -> HttpResponse:
    """
    Renderiza a tela de carregamento ou processa o POST via AJAX para disparar a sincronização.
    """
    empresa = request.user.perfil.empresa
    
    if request.method == 'POST':
        try:
            service = OmieService(empresa)
            sync_obj = service.processar_sincronizacao_preview()
            return JsonResponse({'status': 'ok', 'sync_id': sync_obj.id})
        except ValueError as ve:
            return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Erro de comunicação com o Omie: {str(e)}"}, status=500)
            
    return render(request, 'painel/omie/sincronizar.html', {'empresa': empresa})


@login_required
def omie_validacao_view(request: HttpRequest, sync_id: int) -> HttpResponse:
    """
    Tela de preview onde o usuário seleciona (checkbox) os produtos novos 
    e alterados antes de salvar no banco de dados definitivo.
    """
    empresa = request.user.perfil.empresa
    sync_obj = get_object_or_404(SincronizacaoOmie, id=sync_id, empresa=empresa, status=SincronizacaoOmie.Status.PENDENTE)
    
    dados = sync_obj.dados
    novos = dados.get('novos', [])
    alterados = dados.get('alterados', [])
    metricas = dados.get('metricas', {})
    
    # Agrupar por família para renderizar os acordeões
    familias_dict = {}
    
    for item in novos:
        item['tipo'] = 'novo'
        fam = item.get('familia', 'Sem Categoria')
        if fam not in familias_dict:
            familias_dict[fam] = []
        familias_dict[fam].append(item)
        
    for item in alterados:
        item['tipo'] = 'alterado'
        fam = item.get('familia', 'Sem Categoria')
        if fam not in familias_dict:
            familias_dict[fam] = []
        familias_dict[fam].append(item)

    context = {
        'sync_obj': sync_obj,
        'familias_dict': familias_dict,
        'metricas': metricas
    }
    return render(request, 'painel/omie/validacao.html', context)


@login_required
@require_POST
def omie_efetivar_view(request: HttpRequest, sync_id: int) -> HttpResponse:
    """
    Recebe os checkboxes da tela de validação, efetiva as mudanças no BD 
    e registra itens na deny list, se necessário.
    """
    empresa = request.user.perfil.empresa
    
    aprovados = request.POST.getlist('aprovados')
    denylist = request.POST.getlist('denylist')
    
    try:
        service = OmieService(empresa)
        criados, atualizados = service.efetivar_sincronizacao(sync_id, aprovados, denylist)
        messages.success(request, f"Sincronização concluída! {criados} novos produtos criados, {atualizados} preços atualizados.")
        return redirect('produtos_list')
    except Exception as e:
        messages.error(request, f"Erro ao efetivar sincronização: {str(e)}")
        return redirect('omie_validacao', sync_id=sync_id)


class DenyListListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    """
    Lista todos os produtos ignorados (Deny List) da empresa.
    """
    model = ProdutoIgnoradoOmie
    template_name = 'painel/omie/denylist.html'
    context_object_name = 'ignorados'
    paginate_by = 30
    
    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(codigo__icontains=q) | Q(descricao__icontains=q))
        return qs.order_by('-created_at')

class DenyListDeleteView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, DeleteView):
    """
    Remove um produto da Deny List, permitindo que ele volte a aparecer nas próximas sincronizações.
    """
    model = ProdutoIgnoradoOmie
    success_url = reverse_lazy('omie_denylist')
    success_message = "Produto removido da Deny List. Ele aparecerá na próxima sincronização."
    
    def get(self, request, *args, **kwargs):
        # Permitir deletar via POST apenas, redirecionar se for GET ou implementar soft delete
        return self.post(request, *args, **kwargs)

@login_required
@require_POST
def omie_ignorar_familia_view(request: HttpRequest, sync_id: int) -> HttpResponse:
    """
    Ignora permanentemente uma família do Omie.
    Cria a regra no banco e expurga a família do preview atual.
    """
    empresa = request.user.perfil.empresa
    familia_nome = request.POST.get('familia_nome')
    
    if not familia_nome:
        messages.error(request, "Nome da família não fornecido.")
        return redirect('omie_validacao', sync_id=sync_id)

    # 1. Cria a regra no banco
    FamiliaIgnoradaOmie.objects.get_or_create(empresa=empresa, nome=familia_nome)
    
    # 2. Expurga a família do sync_obj atual (para sumir da tela imediatamente)
    sync_obj = get_object_or_404(SincronizacaoOmie, id=sync_id, empresa=empresa)
    dados = sync_obj.dados
    
    if 'novos' in dados:
        dados['novos'] = [item for item in dados['novos'] if item.get('familia') != familia_nome]
    if 'alterados' in dados:
        dados['alterados'] = [item for item in dados['alterados'] if item.get('familia') != familia_nome]
        
    sync_obj.dados = dados
    sync_obj.save()
    
    messages.success(request, f"Família '{familia_nome}' ignorada com sucesso. Ela não aparecerá mais.")
    return redirect('omie_validacao', sync_id=sync_id)

class FamiliasIgnoradasListView(LoginRequiredMixin, TenantQuerySetMixin, ListView):
    """
    Lista todas as famílias ignoradas permanentemente da empresa.
    """
    model = FamiliaIgnoradaOmie
    template_name = 'painel/omie/familias_ignoradas.html'
    context_object_name = 'ignoradas'
    paginate_by = 30
    
    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(nome__icontains=q)
        return qs.order_by('-created_at')

class FamiliaIgnoradaDeleteView(LoginRequiredMixin, SuccessMessageMixin, TenantQuerySetMixin, DeleteView):
    """
    Remove uma família da Deny List, permitindo que ela volte a aparecer nas próximas sincronizações.
    """
    model = FamiliaIgnoradaOmie
    success_url = reverse_lazy('omie_familias_ignoradas')
    success_message = "Família removida da Deny List. Ela aparecerá na próxima sincronização."
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


# ==============================================================================
#                          CONFIGURAÇÕES E INTEGRAÇÕES
# ==============================================================================

class ConfiguracaoIntegracoesView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    View para gerenciar as credenciais de integrações de terceiros (ex: Omie ERP) da Empresa.
    """
    model = Empresa
    form_class = IntegracoesForm
    template_name = 'painel/configuracoes/integracoes.html'
    success_url = reverse_lazy('configuracao_integracoes')
    success_message = "Configurações de integração atualizadas com sucesso!"

    def get_object(self, queryset=None):
        return self.request.user.perfil.empresa