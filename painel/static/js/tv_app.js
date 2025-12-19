document.addEventListener('DOMContentLoaded', () => {
    const setupScreen = document.getElementById('setup-screen');
    const appScreen = document.getElementById('app-screen');
    const inputCodigo = document.getElementById('input-uuid');
    const btnSalvar = document.getElementById('btn-salvar');
    const elTitulo = document.getElementById('titulo-painel');
    const elConteudo = document.getElementById('painel-conteudo');
    const elVideoContainer = document.getElementById('video-overlay-container');

    let deviceUUID = localStorage.getItem('tv_device_uuid');
    let dadosCache = null;
    
    let modoAtual = 'TABELA';
    let paginaTabelaAtual = 0;
    let indiceVideoAtual = 0;
    
    // Configuração Dinâmica de Layout
    let ITENS_POR_PAGINA = 18; // Padrão Horizontal
    let MODO_VERTICAL = false;

    const TEMPO_PAGINA_TABELA = 12000; 

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

            // 1. Configurações Visuais
            if (data.config && data.config.titulo_exibicao) {
                elTitulo.innerText = data.config.titulo_exibicao;
            }

            // 2. DETECÇÃO DE ORIENTAÇÃO (CRÍTICO)
            document.body.classList.remove('rotacao-90', 'rotacao-270');
            elConteudo.classList.remove('layout-vertical'); // Reseta
            
            const ori = data.config.orientacao;
            if (ori === 'VERTICAL_DIR') {
                document.body.classList.add('rotacao-90');
                MODO_VERTICAL = true;
            } else if (ori === 'VERTICAL_ESQ') {
                document.body.classList.add('rotacao-270');
                MODO_VERTICAL = true;
            } else {
                MODO_VERTICAL = false;
            }

            // Define capacidade da página baseado na orientação
            if (MODO_VERTICAL) {
                ITENS_POR_PAGINA = 15; // 1 Coluna x 15 Linhas
                elConteudo.classList.add('layout-vertical');
            } else {
                ITENS_POR_PAGINA = 18; // 2 Colunas x 9 Linhas
            }

            // 3. Verifica Mudanças e Inicia Ciclo
            const hashNovo = JSON.stringify(data.produtos) + JSON.stringify(data.playlist_final) + data.config.modo_exibicao + data.config.orientacao;
            const hashAntigo = dadosCache ? (JSON.stringify(dadosCache.produtos) + JSON.stringify(dadosCache.playlist_final) + dadosCache.config.modo_exibicao + dadosCache.config.orientacao) : "";

            if (hashNovo !== hashAntigo) {
                console.log("Novos dados/configuração recebidos! Vertical:", MODO_VERTICAL);
                const primeiraCarga = dadosCache === null;
                dadosCache = data;
                
                if (primeiraCarga) {
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

    // --- CICLO DE EXIBIÇÃO ---
    function proximoPassoCiclo() {
        if (!dadosCache) return;

        const configModo = dadosCache.config.modo_exibicao; 
        const temVideos = dadosCache.playlist_final && dadosCache.playlist_final.length > 0;
        const temProdutos = dadosCache.produtos && dadosCache.produtos.length > 0;

        if (configModo === 'TABELA') modoAtual = 'TABELA';
        if (configModo === 'VIDEO') modoAtual = 'VIDEO';

        if (modoAtual === 'TABELA') {
            if (!temProdutos && temVideos && configModo !== 'TABELA') {
                modoAtual = 'VIDEO';
                proximoPassoCiclo();
                return;
            }

            const totalPaginas = Math.ceil(dadosCache.produtos.length / ITENS_POR_PAGINA);
            
            if (temProdutos) {
                renderizarTabela(paginaTabelaAtual);
            } else {
                elConteudo.innerHTML = "<h2>Aguardando produtos...</h2>";
            }

            if (paginaTabelaAtual < totalPaginas - 1) {
                paginaTabelaAtual++;
                setTimeout(proximoPassoCiclo, TEMPO_PAGINA_TABELA);
            } else {
                if (configModo === 'MISTO' && temVideos) {
                    modoAtual = 'VIDEO';
                    indiceVideoAtual = 0;
                    setTimeout(proximoPassoCiclo, TEMPO_PAGINA_TABELA); 
                } else {
                    paginaTabelaAtual = 0;
                    setTimeout(proximoPassoCiclo, TEMPO_PAGINA_TABELA);
                }
            }
        } 
        
        else if (modoAtual === 'VIDEO') {
            if (!temVideos) {
                modoAtual = 'TABELA';
                proximoPassoCiclo();
                return;
            }

            if (indiceVideoAtual < dadosCache.playlist_final.length) {
                const item = dadosCache.playlist_final[indiceVideoAtual];
                mostrarOverlayVideo(item, () => {
                    indiceVideoAtual++;
                    proximoPassoCiclo();
                });
            } else {
                if (configModo === 'MISTO') {
                    modoAtual = 'TABELA';
                    paginaTabelaAtual = 0;
                    esconderOverlayVideo();
                    proximoPassoCiclo();
                } else {
                    indiceVideoAtual = 0;
                    proximoPassoCiclo();
                }
            }
        }
    }

    // --- RENDERIZADOR DA TABELA INTELIGENTE ---
    function renderizarTabela(pagina) {
        esconderOverlayVideo(); 
        elConteudo.classList.add('fade'); 

        setTimeout(() => {
            elConteudo.innerHTML = ''; 
            
            const inicio = pagina * ITENS_POR_PAGINA;
            const fim = inicio + ITENS_POR_PAGINA;
            const produtosReais = dadosCache.produtos.slice(inicio, fim);
            
            // LÓGICA DE COLUNAS
            if (MODO_VERTICAL) {
                // MODO 1 COLUNA (Vertical)
                const col = document.createElement('div'); 
                col.className = 'coluna';
                
                produtosReais.forEach(p => col.appendChild(criarItemHTML(p)));
                
                // Preenche espaço vazio para manter layout
                while (col.children.length < ITENS_POR_PAGINA) {
                    col.appendChild(criarItemVazio());
                }
                
                elConteudo.appendChild(col);

            } else {
                // MODO 2 COLUNAS (Horizontal)
                const col1 = document.createElement('div'); col1.className = 'coluna';
                const col2 = document.createElement('div'); col2.className = 'coluna';
                const itensPorCol = Math.ceil(ITENS_POR_PAGINA / 2); // 9

                produtosReais.forEach((p, idx) => {
                    if (idx < itensPorCol) col1.appendChild(criarItemHTML(p));
                    else col2.appendChild(criarItemHTML(p));
                });

                while (col1.children.length < itensPorCol) col1.appendChild(criarItemVazio());
                while (col2.children.length < itensPorCol) col2.appendChild(criarItemVazio());

                elConteudo.appendChild(col1);
                elConteudo.appendChild(col2);
            }
            
            elConteudo.classList.remove('fade');
        }, 500);
    }

    function criarItemHTML(produto) {
        const div = document.createElement('div');
        div.className = `item-produto ${produto.em_oferta ? 'em-oferta' : ''}`;
        
        const preco = parseFloat(produto.preco).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
        // Ajuste no marquee: Em vertical temos mais largura (1080px vs 960px), então cabe mais texto antes de rodar
        const limiteChars = MODO_VERTICAL ? 28 : 22;
        const nomeClass = produto.descricao.length > limiteChars ? 'nome-container marquee' : 'nome-container';

        div.innerHTML = `
            <div class="${nomeClass}"><span class="nome">${produto.descricao}</span></div>
            <div class="preco">${preco}</div>
        `;
        return div;
    }

    function criarItemVazio() {
        const div = document.createElement('div');
        div.className = 'item-produto';
        div.innerHTML = `<div class="nome-container"><span class="nome">&nbsp;</span></div><div class="preco">&nbsp;</div>`;
        return div;
    }

    // --- RENDERIZADOR DE VÍDEO ---
    function mostrarOverlayVideo(item, onComplete) {
        elVideoContainer.innerHTML = '';
        elVideoContainer.style.display = 'block';

        const isPropaganda = item.tipo === 'propaganda';
        const videoUrl = isPropaganda ? item.url : item.template_video.arquivo_video;

        const video = document.createElement('video');
        video.id = 'video-bg';
        video.src = videoUrl;
        video.muted = true; video.autoplay = true; video.playsInline = true;
        
        const duracaoSeguranca = (item.duracao || 15) * 1000 + 2000; 
        const safetyTimeout = setTimeout(onComplete, duracaoSeguranca);

        video.onerror = () => { clearTimeout(safetyTimeout); onComplete(); };
        video.onended = () => { clearTimeout(safetyTimeout); onComplete(); };
        elVideoContainer.appendChild(video);

        if (isPropaganda) return;

        const template = item.template_video;
        const css = template.estilos_css || {};

        const createEl = (conteudo, top, left, styleBase, estilosExtras) => {
            if (estilosExtras && estilosExtras.display === 'none') return null;

            const el = document.createElement('div');
            el.className = 'overlay-element pop-in';
            
            if (conteudo.startsWith('<img')) el.innerHTML = conteudo;
            else el.innerText = conteudo;

            el.style.top = top + '%';
            el.style.left = left + '%';
            el.style.transform = `translate(-50%, -50%)`; 

            const styleFinal = { ...styleBase, ...estilosExtras };
            if (styleFinal.fontSizeVh) el.style.fontSize = styleFinal.fontSizeVh + 'vh';
            else if (styleFinal.fontSize) el.style.fontSize = styleFinal.fontSize;
            
            ['color', 'backgroundColor', 'fontFamily', 'fontWeight', 'fontStyle', 'textDecoration', 'width', 'height', 'zIndex'].forEach(prop => {
                if(styleFinal[prop]) el.style[prop] = styleFinal[prop];
            });

            return el;
        };

        const elTit = createEl(item.descricao, template.titulo_top, template.titulo_left, { color: template.titulo_cor }, css['el-titulo']);
        if(elTit) elVideoContainer.appendChild(elTit);
        
        const precoVal = parseFloat(item.preco).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
        const elPreco = createEl(precoVal, template.preco_top, template.preco_left, { color: template.preco_cor }, css['el-preco']);
        if(elPreco) elVideoContainer.appendChild(elPreco);

        if (item.imagem) {
            const imgHTML = `<img src="${item.imagem}" style="width:100%; height:100%; object-fit:contain;">`;
            const elImg = createEl(imgHTML, template.img_top, template.img_left, { width: template.img_width + '%' }, css['el-imagem']);
            if(elImg) elVideoContainer.appendChild(elImg);
        }

        if (template.elementos_extras) {
            template.elementos_extras.forEach(extra => {
                const el = createEl(extra.texto, extra.top, extra.left, {}, extra.style);
                if(el) elVideoContainer.appendChild(el);
            });
        }
    }

    function esconderOverlayVideo() {
        elVideoContainer.style.display = 'none';
        elVideoContainer.innerHTML = '';
    }
});