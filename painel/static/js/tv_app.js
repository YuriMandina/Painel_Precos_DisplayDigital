document.addEventListener('DOMContentLoaded', () => {
    // Referências do DOM
    const setupScreen = document.getElementById('setup-screen');
    const appScreen = document.getElementById('app-screen');
    const inputCodigo = document.getElementById('input-uuid');
    const btnSalvar = document.getElementById('btn-salvar');
    const elTitulo = document.getElementById('titulo-painel');
    const elConteudo = document.getElementById('painel-conteudo');
    const elVideoContainer = document.getElementById('video-overlay-container');

    // Estado da Aplicação
    let deviceUUID = localStorage.getItem('tv_device_uuid');
    let dadosCache = null;
    
    // Controle de Ciclo
    let modoAtual = 'TABELA'; // Estado inicial padrão
    let paginaTabelaAtual = 0;
    let indiceVideoAtual = 0;
    
    // Constantes de Tempo
    const TEMPO_PAGINA_TABELA = 12000; // 12s por página da tabela
    const ITENS_POR_PAGINA = 18;

    // --- SETUP ---
    if(inputCodigo) inputCodigo.placeholder = "CÓDIGO DE 6 DÍGITOS";

    if (!deviceUUID) {
        mostrarSetup();
    } else {
        iniciarApp();
    }

    // --- PAREAMENTO ---
    btnSalvar.addEventListener('click', async () => {
        const codigo = inputCodigo.value.trim();
        if (codigo.length < 2) return alert("Digite o código.");

        try {
            const response = await fetch('/api/painel/parear/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ codigo: codigo })
            });

            if (!response.ok) {
                // Tenta pegar msg de erro do backend
                let msg = "Erro desconhecido";
                try { const json = await response.json(); msg = json.erro || msg; } catch(e){}
                throw new Error(msg);
            }

            const data = await response.json();
            localStorage.setItem('tv_device_uuid', data.uuid);
            deviceUUID = data.uuid;
            iniciarApp();

        } catch (error) {
            alert(error.message);
        }
    });

    function mostrarSetup() {
        setupScreen.style.display = 'flex';
        appScreen.style.display = 'none';
    }

    function iniciarApp() {
        setupScreen.style.display = 'none';
        appScreen.style.display = 'flex';
        carregarDados();
        setInterval(carregarDados, 60000); 
    }

    // --- BUSCA DE DADOS ---
    async function carregarDados() {
        try {
            const response = await fetch(`/api/painel/${deviceUUID}/`);
            if (!response.ok) throw new Error("Erro API");
            const data = await response.json();

            if (data.config && data.config.titulo_exibicao) {
                elTitulo.innerText = data.config.titulo_exibicao;
            }

            const hashNovo = JSON.stringify(data.produtos) + JSON.stringify(data.ofertas_destaque) + data.config.modo_exibicao;
            const hashAntigo = dadosCache ? (JSON.stringify(dadosCache.produtos) + JSON.stringify(dadosCache.ofertas_destaque) + dadosCache.config.modo_exibicao) : "";

            if (hashNovo !== hashAntigo) {
                console.log("Novos dados/configuração recebidos!");
                const primeiraCarga = dadosCache === null;
                dadosCache = data;
                
                // Se mudou a configuração (Ex: de Tabela para Video), forçamos o reset do ciclo
                if (primeiraCarga) {
                    // Define o modo inicial baseado na config
                    if (dadosCache.config.modo_exibicao === 'VIDEO') {
                        modoAtual = 'VIDEO';
                    } else {
                        modoAtual = 'TABELA';
                    }
                    proximoPassoCiclo();
                }
            }
        } catch (e) { console.error(e); }
    }

    // --- MOTOR DE DECISÃO (CORRIGIDO) ---
    function proximoPassoCiclo() {
        if (!dadosCache) return;

        const configModo = dadosCache.config.modo_exibicao; // 'TABELA', 'VIDEO' ou 'MISTO'
        const temVideos = dadosCache.ofertas_destaque && dadosCache.ofertas_destaque.length > 0;
        const temProdutos = dadosCache.produtos && dadosCache.produtos.length > 0;

        // 1. Força o Estado baseado na Configuração
        // Se a config diz "SÓ TABELA", proibido estar em modo VIDEO.
        if (configModo === 'TABELA') modoAtual = 'TABELA';
        // Se a config diz "SÓ VIDEO", proibido estar em modo TABELA.
        if (configModo === 'VIDEO') modoAtual = 'VIDEO';


        // 2. Executa a lógica do Estado Atual
        if (modoAtual === 'TABELA') {
            
            // Segurança: Se não tem produtos, mas tem vídeos e é MISTO/VIDEO, troca.
            if (!temProdutos && temVideos && configModo !== 'TABELA') {
                modoAtual = 'VIDEO';
                proximoPassoCiclo();
                return;
            }

            const totalPaginas = Math.ceil(dadosCache.produtos.length / ITENS_POR_PAGINA);
            
            // Renderiza se tiver o que mostrar
            if (temProdutos) {
                renderizarTabela(paginaTabelaAtual);
            } else {
                elConteudo.innerHTML = "<h2>Sem produtos para exibir</h2>";
            }

            // Lógica de Transição
            if (paginaTabelaAtual < totalPaginas - 1) {
                // Ainda tem páginas de tabela
                paginaTabelaAtual++;
                setTimeout(proximoPassoCiclo, TEMPO_PAGINA_TABELA);
            } else {
                // Chegou na última página da tabela. O que fazer agora?
                
                if (configModo === 'MISTO' && temVideos) {
                    // SE for misto E tiver vídeos -> Vai para Vídeo
                    modoAtual = 'VIDEO';
                    indiceVideoAtual = 0;
                    setTimeout(proximoPassoCiclo, TEMPO_PAGINA_TABELA); // Espera ler a última pág antes de trocar
                } else {
                    // SE for só tabela OU não tiver vídeos -> Volta pro início da Tabela
                    paginaTabelaAtual = 0;
                    setTimeout(proximoPassoCiclo, TEMPO_PAGINA_TABELA);
                }
            }
        } 
        
        else if (modoAtual === 'VIDEO') {
            // Segurança: Se não tem vídeos, volta pra tabela
            if (!temVideos) {
                modoAtual = 'TABELA';
                proximoPassoCiclo();
                return;
            }

            if (indiceVideoAtual < dadosCache.ofertas_destaque.length) {
                // Toca o vídeo atual
                const oferta = dadosCache.ofertas_destaque[indiceVideoAtual];
                mostrarOverlayVideo(oferta, () => {
                    // Quando acabar o vídeo:
                    indiceVideoAtual++;
                    proximoPassoCiclo();
                });
            } else {
                // Acabaram os vídeos da lista. O que fazer?
                
                if (configModo === 'MISTO') {
                    // SE for misto -> Volta para Tabela
                    modoAtual = 'TABELA';
                    paginaTabelaAtual = 0;
                    esconderOverlayVideo();
                    proximoPassoCiclo();
                } else {
                    // SE for só vídeo -> Loop infinito nos vídeos
                    indiceVideoAtual = 0;
                    proximoPassoCiclo();
                }
            }
        }
    }

// --- RENDERIZADOR DA TABELA (COM CORREÇÃO VISUAL) ---
    function renderizarTabela(pagina) {
        esconderOverlayVideo(); 
        elConteudo.classList.add('fade'); 

        setTimeout(() => {
            elConteudo.innerHTML = ''; 
            
            const inicio = pagina * ITENS_POR_PAGINA;
            const fim = inicio + ITENS_POR_PAGINA;
            // Pega os produtos reais
            const produtosReais = dadosCache.produtos.slice(inicio, fim);
            
            // Cria arrays para as colunas
            const itensCol1 = [];
            const itensCol2 = [];

            // 1. Distribui produtos reais
            produtosReais.forEach((p, idx) => {
                if (idx < 9) itensCol1.push(criarItemHTML(p));
                else itensCol2.push(criarItemHTML(p));
            });

            // 2. Preenchimento de Espaços Vazios (Dummy Items)
            // Garante que a coluna 1 tenha sempre 9 itens
            while (itensCol1.length < 9) {
                itensCol1.push(criarItemVazio());
            }
            // Garante que a coluna 2 tenha sempre 9 itens
            while (itensCol2.length < 9) {
                itensCol2.push(criarItemVazio());
            }

            // 3. Renderiza no DOM
            const col1Div = document.createElement('div'); col1Div.className = 'coluna';
            const col2Div = document.createElement('div'); col2Div.className = 'coluna';

            itensCol1.forEach(el => col1Div.appendChild(el));
            itensCol2.forEach(el => col2Div.appendChild(el));

            elConteudo.appendChild(col1Div);
            elConteudo.appendChild(col2Div);
            
            elConteudo.classList.remove('fade');
        }, 500);
    }

    // Cria o HTML do Produto Real
    function criarItemHTML(produto) {
        const div = document.createElement('div');
        div.className = `item-produto ${produto.em_oferta ? 'em-oferta' : ''}`;
        
        const preco = parseFloat(produto.preco).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
        const nomeClass = produto.descricao.length > 18 ? 'nome-container marquee' : 'nome-container';

        div.innerHTML = `
            <div class="${nomeClass}"><span class="nome">${produto.descricao}</span></div>
            <div class="preco">${preco}</div>
        `;
        return div;
    }

    // Cria o HTML de Espaço Vazio (mantém a linha pontilhada)
    function criarItemVazio() {
        const div = document.createElement('div');
        div.className = 'item-produto';
        // Conteúdo invisível para manter altura
        div.innerHTML = `
            <div class="nome-container"><span class="nome">&nbsp;</span></div>
            <div class="preco">&nbsp;</div>
        `;
        return div;
    }

    // --- RENDERIZADOR DE VÍDEO (OVERLAY) ---
    function mostrarOverlayVideo(oferta, onComplete) {
        const template = oferta.template_video;
        if (!template) { onComplete(); return; }

        elVideoContainer.innerHTML = '';
        elVideoContainer.style.display = 'block';

        const video = document.createElement('video');
        video.id = 'video-bg';
        video.src = template.arquivo_video;
        video.muted = true;
        video.autoplay = true;
        video.playsInline = true;
        
        // Timeout de segurança: Se o vídeo travar ou não carregar em 15s, pula
        const safetyTimeout = setTimeout(onComplete, 15000);

        video.onerror = () => { clearTimeout(safetyTimeout); onComplete(); };
        video.onended = () => { clearTimeout(safetyTimeout); onComplete(); };

        elVideoContainer.appendChild(video);

        // Função auxiliar para criar elementos
        const createEl = (cls, txt, top, left, col, size, delay) => {
            const el = document.createElement('div');
            el.className = `overlay-element ${cls}`;
            el.innerText = txt;
            el.style.top = top + '%';
            el.style.left = left + '%';
            el.style.color = col;
            el.style.fontSize = size;
            el.style.transform = 'translate(-50%, -50%)';
            if(delay) el.style.animationDelay = delay;
            return el;
        };

        elVideoContainer.appendChild(createEl('pop-in', oferta.descricao, template.titulo_top, template.titulo_left, template.titulo_cor, template.titulo_tamanho));
        
        const precoVal = parseFloat(oferta.preco).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
        elVideoContainer.appendChild(createEl('pop-in', precoVal, template.preco_top, template.preco_left, template.preco_cor, template.preco_tamanho, '0.3s'));

        if (oferta.imagem) {
            const img = document.createElement('img');
            img.className = 'overlay-img pop-in';
            img.src = oferta.imagem;
            img.style.top = template.img_top + '%';
            img.style.left = template.img_left + '%';
            img.style.width = template.img_width + '%';
            img.style.transform = 'translate(-50%, -50%)';
            elVideoContainer.appendChild(img);
        }
    }

    function esconderOverlayVideo() {
        elVideoContainer.style.display = 'none';
        elVideoContainer.innerHTML = '';
    }
});