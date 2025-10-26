document.addEventListener('DOMContentLoaded', () => {

    // Selecionar os elementos de input do filtro
    const filtroCodigo = document.getElementById('filtro-codigo');
    const filtroNome = document.getElementById('filtro-nome');
    
    //Selecionar todas as linhas de produtos da tabela
    const linhasProdutos = document.querySelectorAll('#tabela-produtos-corpo .produto-item');

    // Criar a função que aplica o filtro
    function aplicarFiltros() {
        const termoCodigo = filtroCodigo.value.toLowerCase().trim();
        const termoNome = filtroNome.value.toLowerCase().trim();

        // assa por cada linha de produto
        linhasProdutos.forEach(linha => {
            
            //5. Pega o conteúdo de texto de cada célula da linha
            const textoCodigo = linha.querySelector('.produto-codigo').textContent.toLowerCase().trim();
            const textoNome = linha.querySelector('.produto-nome input').value.toLowerCase().trim();

            // Verifica se a linha corresponde a TODOS os filtros preenchidos
            const matchCodigo = textoCodigo.includes(termoCodigo);
            const matchNome = textoNome.includes(termoNome);

            // Mostra ou esconde a linha com base na correspondência
            if (matchCodigo && matchNome) {
                // Se der "match" em tudo, mostra a linha
                linha.style.display = ''; // Reseta para o padrão (table-row)
            } else {
                // Se qualquer filtro falhar, esconde a linha
                linha.style.display = 'none';
            }
        });
    }

    // Adicionar "escutadores" de eventos nos inputs
    filtroCodigo.addEventListener('input', aplicarFiltros);
    filtroNome.addEventListener('input', aplicarFiltros);

});