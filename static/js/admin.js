document.addEventListener('DOMContentLoaded', () => {

    // --- LÓGICA DE FILTRO ---
    const filtroCodigo = document.getElementById('filtro-codigo');
    const filtroNome = document.getElementById('filtro-nome');
    const tabelaCorpo = document.getElementById('tabela-produtos-corpo'); // Alvo para novos produtos

    function aplicarFiltros() {
        const termoCodigo = filtroCodigo.value.toLowerCase().trim();
        const termoNome = filtroNome.value.toLowerCase().trim();
        
        // Seleciona as linhas dentro do corpo da tabela
        const linhasProdutos = tabelaCorpo.querySelectorAll('.produto-item');

        linhasProdutos.forEach(linha => {
            const textoCodigo = linha.querySelector('.produto-codigo').textContent.toLowerCase().trim();
            const textoNome = linha.querySelector('.produto-nome input').value.toLowerCase().trim();
            const matchCodigo = textoCodigo.includes(termoCodigo);
            const matchNome = textoNome.includes(termoNome);

            if (matchCodigo && matchNome) {
                linha.style.display = '';
            } else {
                linha.style.display = 'none';
            }
        });
    }

    if (filtroCodigo && filtroNome) {
        filtroCodigo.addEventListener('input', aplicarFiltros);
        filtroNome.addEventListener('input', aplicarFiltros);
    }

    const alertPlaceholder = document.getElementById('ajax-alerts-placeholder');
    const formAddProduto = document.getElementById('form-add-produto');

    // Função helper para mostrar alertas
    function showAjaxAlert(message, category = 'success') {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) return; // Sai se o contêiner não existir

    // Define o estilo do toast
    const bgClass = category === 'success' ? 'text-bg-success' : 'text-bg-danger';
    const title = category === 'success' ? 'Sucesso!' : 'Erro!';

    // Cria o elemento toast
    const wrapper = document.createElement('div');
    wrapper.innerHTML = [
        `<div class="toast ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true" data-bs-autohide="true" data-bs-delay="5000">`,
        '  <div class="toast-header">',
        `    <strong class="me-auto">${title}</strong>`,
        '    <small>agora mesmo</small>',
        '    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>',
        '  </div>',
        `  <div class="toast-body">${message}</div>`,
        '</div>'
    ].join('');

    const toastElement = wrapper.firstChild;

    // Adiciona um listener para remover o toast do DOM depois que ele sumir
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });

    // Adiciona o toast ao contêiner
    toastContainer.append(toastElement);

    // Inicializa e mostra o toast
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
}

    // Função helper para criar uma nova linha na tabela
    function createNewTableRow(produto) {
        const newRow = document.createElement('tr');
        newRow.classList.add('produto-item');
        
        // URLs que o servidor geraria com url_for()
        const updateUrl = `/admin/update/${produto.id}`;
        const deleteUrl = `/admin/delete/${produto.id}`;

        newRow.innerHTML = `
            <form action="${updateUrl}" method="POST" class="form-update-produto">
                <td class="produto-codigo">${produto.codigo}</td>
                <td class="produto-nome"><input type="text" name="nome" value="${produto.nome}" class="form-control form-control-sm"></td>
                <td><input type="text" name="preco" value="${produto.preco}" class="form-control form-control-sm"></td>
                <td class="text-center">
                    <div class="form-check d-flex justify-content-center">
                        <input type="checkbox" name="no_painel" class="form-check-input" ${produto.no_painel ? 'checked' : ''}>
                    </div>
                </td>
                <td class="text-center">
                    <div class="form-check d-flex justify-content-center">
                        <input type="checkbox" name="em_oferta" class="form-check-input" ${produto.em_oferta ? 'checked' : ''}>
                    </div>
                </td>
                <td>
                    <button type="submit" class="btn btn-primary btn-sm">Salvar</button>
                    <button type="button" class="btn btn-danger btn-sm btn-delete-produto" data-url="${deleteUrl}">Deletar</button>
                </td>
            </form>
        `;
        tabelaCorpo.prepend(newRow);
    }

    // Listener para adicionar produto
    if (formAddProduto) {
        formAddProduto.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(formAddProduto);
            
            try {
                const response = await fetch(formAddProduto.action, {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (data.success) {
                    showAjaxAlert(data.message, 'success');
                    createNewTableRow(data.produto);
                    formAddProduto.reset();
                } else {
                    showAjaxAlert(data.message, 'error');
                }
            } catch (error) {
                showAjaxAlert('Erro de conexão ao tentar adicionar.', 'error');
            }
        });
    }

    // Listeners para atualizar e deletar
    if (tabelaCorpo) {
        tabelaCorpo.addEventListener('submit', async (e) => {
            if (e.target.classList.contains('form-update-produto')) {
                e.preventDefault();
                const form = e.target;
                const formData = new FormData(form);

                try {
                    const response = await fetch(form.action, {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();

                    if (data.success) {
                        showAjaxAlert(data.message, 'success');
                    } else {
                        showAjaxAlert(data.message, 'error');
                    }
                } catch (error) {
                    showAjaxAlert('Erro de conexão ao tentar atualizar.', 'error');
                }
            }
        });

        tabelaCorpo.addEventListener('click', async (e) => {
            if (e.target.classList.contains('btn-delete-produto')) {
                e.preventDefault();
                
                if (!confirm('Tem certeza que deseja deletar este produto?')) {
                    return;
                }

                const button = e.target;
                const url = button.dataset.url;

                try {
                    const response = await fetch(url, {
                        method: 'POST'
                    });
                    const data = await response.json();

                    if (data.success) {
                        showAjaxAlert(data.message, 'success');
                        button.closest('tr').remove();
                    } else {
                        showAjaxAlert(data.message, 'error');
                    }
                } catch (error) {
                    showAjaxAlert('Erro de conexão ao tentar deletar.', 'error');
                }
            }
        });
    }
});