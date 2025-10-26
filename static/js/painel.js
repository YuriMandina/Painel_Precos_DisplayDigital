document.addEventListener('DOMContentLoaded', function() {
    
    const painel = document.getElementById('painel-conteudo');
        
    const TEMPO_POR_PAGINA = 8000;
    const TEMPO_FADE = 500;
    
    // Calcula o número de produtos por coluna (metade do total por página)
    const produtosPorColuna = Math.ceil(PRODUTOS_POR_PAGINA / 2);
    
    // Calcula o número total de páginas
    const totalPaginas = Math.ceil(TODOS_PRODUTOS.length / PRODUTOS_POR_PAGINA);
    
    let paginaAtual = 0;

    function formatarPreco(preco) {
        // Formata para o padrão R$ 1.234,56
        return preco.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    function carregarPagina(pagina) {
        // Adiciona a classe 'fade' para sumir com o conteúdo
        painel.classList.add('fade');

        // Espera a animação de fade-out terminar
        setTimeout(() => {
            // Limpa o painel
            painel.innerHTML = '';

            // Calcula quais produtos mostrar
            const inicio = pagina * PRODUTOS_POR_PAGINA;
            const fim = inicio + PRODUTOS_POR_PAGINA;
            const produtosDaPagina = TODOS_PRODUTOS.slice(inicio, fim);
            
            // Cria as colunas
            const coluna1 = document.createElement('div');
            coluna1.className = 'coluna';
            const coluna2 = document.createElement('div');
            coluna2.className = 'coluna';

            // Distribui os produtos nas colunas
            produtosDaPagina.forEach((produto, index) => {
                const itemProduto = document.createElement('div');
                itemProduto.className = 'item-produto';
                
                // Adiciona classe de oferta
                if (produto.em_oferta) {
                    itemProduto.classList.add('em-oferta');
                }

                itemProduto.innerHTML = `
                    <span class="nome">${produto.nome}</span>
                    <span class="preco">
                        ${formatarPreco(produto.preco)}
                        <span class="tag-oferta">OFERTA</span>
                    </span>
                `;

                // Decide em qual coluna colocar
                if (index < produtosPorColuna) {
                    coluna1.appendChild(itemProduto);
                } else {
                    coluna2.appendChild(itemProduto);
                }
            });

            // Adiciona as colunas ao painel
            painel.appendChild(coluna1);
            painel.appendChild(coluna2);

            // Remove a classe 'fade' para aparecer o novo conteúdo
            painel.classList.remove('fade');

        }, TEMPO_FADE);
    }

    function proximaPagina() {
        paginaAtual++;
        // Loop Infinito
        if (paginaAtual >= totalPaginas) {
            paginaAtual = 0;
        }
        carregarPagina(paginaAtual);
    }

    // Inicia o ciclo
    if (totalPaginas > 0) {
        carregarPagina(0); // Carrega a primeira página
        
        if (totalPaginas > 1) {
            setInterval(proximaPagina, TEMPO_POR_PAGINA);
        }
    } else {
        painel.innerHTML = '<h2>Nenhum produto cadastrado para exibição.</h2>';
    }
});