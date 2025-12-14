document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. Seleção de Elementos ---
    const setupScreen = document.getElementById('setup-screen');
    const appScreen = document.getElementById('app-screen');
    const inputCodigo = document.getElementById('input-uuid');
    const btnSalvar = document.getElementById('btn-salvar');
    
    const elTitulo = document.getElementById('titulo-painel');
    const elConteudo = document.getElementById('painel-conteudo');

    // --- 2. Configurações de Estado ---
    let deviceUUID = localStorage.getItem('tv_device_uuid');
    let dadosCache = null; // Armazena a última resposta da API para comparação
    let paginaAtual = 0;
    
    const ITENS_POR_PAGINA = 18;
    const ITENS_POR_COLUNA = 9; // Metade da página
    const TEMPO_PAGINA_MS = 10000; // 10 segundos por página (Carrossel)
    const TEMPO_POLLING_MS = 60000; // 60 segundos para buscar atualizações no servidor

    // Ajusta Placeholder visualmente
    if (inputCodigo) {
        inputCodigo.placeholder = "CÓDIGO DE 6 DÍGITOS (Ex: A4X9B2)";
    }

    // --- 3. Inicialização ---
    if (!deviceUUID) {
        mostrarSetup();
    } else {
        iniciarApp();
    }

    // --- 4. Lógica de Pareamento (Código Curto) ---
    btnSalvar.addEventListener('click', async () => {
        const codigo = inputCodigo.value.trim();
        
        // Remove validação de tamanho para teste, caso tenha mudado a lógica
        if (codigo.length < 2) {
            alert("Digite o código.");
            return;
        }

        try {
            console.log("Enviando código:", codigo); // Debug

            const response = await fetch('/api/painel/parear/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                    // Não enviamos CSRF Token aqui propositalmente
                },
                body: JSON.stringify({ codigo: codigo })
            });

            // LOGICA DE ERRO DETALHADA
            if (!response.ok) {
                // Tenta ler a mensagem de erro que o servidor mandou (JSON)
                let errorMsg = "Erro desconhecido";
                try {
                    const errData = await response.json();
                    errorMsg = errData.erro || JSON.stringify(errData);
                } catch (e) {
                    errorMsg = response.statusText;
                }
                
                throw new Error(`Erro ${response.status}: ${errorMsg}`);
            }

            const data = await response.json();
            console.log("Pareamento sucesso:", data);
            
            localStorage.setItem('tv_device_uuid', data.uuid);
            deviceUUID = data.uuid;
            
            iniciarApp();

        } catch (error) {
            console.error(error);
            alert("FALHA NO PAREAMENTO:\n" + error.message);
        }
    });

    // --- 5. Funções de Controle de Tela ---
    function mostrarSetup() {
        setupScreen.style.display = 'flex';
        appScreen.style.display = 'none';
    }

    function iniciarApp() {
        setupScreen.style.display = 'none';
        appScreen.style.display = 'flex'; // Mantém o flexbox do wrapper
        
        // Primeira carga
        carregarDados();
        
        // Agenda o polling infinito para buscar atualizações
        setInterval(carregarDados, TEMPO_POLLING_MS);
    }

    // --- 6. Consumo da API ---
    async function carregarDados() {
        try {
            const response = await fetch(`/api/painel/${deviceUUID}/`);
            if (!response.ok) throw new Error("Erro de comunicação com API");
            
            const data = await response.json();
            
            // A. Atualiza Título Dinâmico (Ex: "BOVINOS" ou "OFERTAS DO DIA")
            if (data.config && data.config.titulo_exibicao) {
                elTitulo.innerText = data.config.titulo_exibicao;
            }

            // B. Verifica se os produtos mudaram para evitar piscar a tela sem necessidade
            // Cria um "hash" simples transformando o array em string
            const hashNovo = JSON.stringify(data.produtos);
            const hashAntigo = dadosCache ? JSON.stringify(dadosCache.produtos) : "";

            if (hashNovo !== hashAntigo) {
                console.log("Novos dados recebidos. Atualizando renderização...");
                dadosCache = data;
                
                // Reinicia para a primeira página sempre que os dados mudam
                paginaAtual = 0;
                renderizarPagina();
            } else {
                console.log("Nenhuma alteração nos dados.");
            }

        } catch (error) {
            console.error("Falha ao buscar dados:", error);
            // Opcional: Se der erro 404 persistente, poderia limpar o localStorage
        }
    }

    // --- 7. Motor de Renderização (Grid) ---
    function renderizarPagina() {
        // Segurança: Se não tem dados, não faz nada
        if (!dadosCache || !dadosCache.produtos.length) {
            elConteudo.innerHTML = '<h2 style="margin:auto; color:#666;">Aguardando cadastro de produtos...</h2>';
            return;
        }

        // 1. Inicia Animação de Saída (Fade Out)
        elConteudo.classList.add('fade');

        // Aguarda o tempo da transição CSS (0.5s)
        setTimeout(() => {
            // 2. Limpa o Painel
            elConteudo.innerHTML = '';
            
            const totalPaginas = Math.ceil(dadosCache.produtos.length / ITENS_POR_PAGINA);
            
            // Loop Infinito de Páginas
            if (paginaAtual >= totalPaginas) {
                paginaAtual = 0;
            }

            // 3. Fatiamento dos Dados (Slice)
            const inicio = paginaAtual * ITENS_POR_PAGINA;
            const fim = inicio + ITENS_POR_PAGINA;
            const produtosDaPagina = dadosCache.produtos.slice(inicio, fim);

            // 4. Criação das Colunas (Para bater com o CSS Grid)
            const col1 = document.createElement('div'); 
            col1.className = 'coluna';
            const col2 = document.createElement('div'); 
            col2.className = 'coluna';

            // 5. Distribuição dos Produtos nas Colunas
            produtosDaPagina.forEach((produto, index) => {
                const itemDiv = criarItemHTML(produto);
                
                // Os primeiros 9 vão para a esquerda, o resto para a direita
                if (index < ITENS_POR_COLUNA) {
                    col1.appendChild(itemDiv);
                } else {
                    col2.appendChild(itemDiv);
                }
            });

            // Adiciona as colunas ao DOM
            elConteudo.appendChild(col1);
            elConteudo.appendChild(col2);

            // 6. Inicia Animação de Entrada (Fade In)
            elConteudo.classList.remove('fade');

            // 7. Agenda a próxima página (apenas se houver mais de uma página)
            if (totalPaginas > 1) {
                setTimeout(() => {
                    paginaAtual++;
                    renderizarPagina();
                }, TEMPO_PAGINA_MS);
            }

        }, 500); // Tempo idêntico ao transition no CSS
    }

    // --- 8. Gerador de HTML do Item ---
    function criarItemHTML(produto) {
        const div = document.createElement('div');
        div.className = `item-produto ${produto.em_oferta ? 'em-oferta' : ''}`;
        
        // Formatação de preço R$ segura
        const precoFmt = parseFloat(produto.preco).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

        // Lógica Marquee (Scroll Horizontal)
        // Se o texto tiver mais de 22 caracteres, aplica a classe que faz ele rodar
        const isLongName = produto.descricao.length > 22;
        const nomeClass = isLongName ? 'nome-container marquee' : 'nome-container';

        div.innerHTML = `
            <div class="${nomeClass}">
                <span class="nome">${produto.descricao}</span>
            </div>
            <div class="preco">${precoFmt}</div>
        `;
        return div;
    }
});