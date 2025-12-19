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

            // 1. Atualiza Título
            if (data.config && data.config.titulo_exibicao) {
                elTitulo.innerText = data.config.titulo_exibicao;
            }

            // 2. APLICA A ROTAÇÃO
            document.body.classList.remove('rotacao-90', 'rotacao-270');
            
            if (data.config.orientacao === 'VERTICAL_DIR') {
                document.body.classList.add('rotacao-90');
            } else if (data.config.orientacao === 'VERTICAL_ESQ') {
                document.body.classList.add('rotacao-270');
            }

            // 3. Verifica Mudanças (Agora olha para playlist_final)
            // Cria um hash simples do conteúdo
            const hashNovo = JSON.stringify(data.produtos) + JSON.stringify(data.playlist_final) + data.config.modo_exibicao + data.config.orientacao;
            const hashAntigo = dadosCache ? (JSON.stringify(dadosCache.produtos) + JSON.stringify(dadosCache.playlist_final) + dadosCache.config.modo_exibicao + dadosCache.config.orientacao) : "";

            if (hashNovo !== hashAntigo) {
                console.log("Novos dados/configuração recebidos!");
                const primeiraCarga = dadosCache === null;
                dadosCache = data;
                
                // Se mudou a configuração (Ex: de Tabela para Video), forçamos o reset do ciclo
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

    // --- MOTOR DE DECISÃO ---
    function proximoPassoCiclo() {
        if (!dadosCache) return;

        const configModo = dadosCache.config.modo_exibicao; // 'TABELA', 'VIDEO' ou 'MISTO'
        // Agora usamos playlist_final que contém mix de Produtos e Propagandas
        const temVideos = dadosCache.playlist_final && dadosCache.playlist_final.length > 0;
        const temProdutos = dadosCache.produtos && dadosCache.produtos.length > 0;

        // 1. Força o Estado baseado na Configuração
        if (configModo === 'TABELA') modoAtual = 'TABELA';
        if (configModo === 'VIDEO') modoAtual = 'VIDEO';

        // 2. Executa a lógica do Estado Atual
        if (modoAtual === 'TABELA') {
            
            // Segurança: Se não tem produtos na tabela, mas tem vídeos e é MISTO/VIDEO, troca.
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

            // Lógica de Transição
            if (paginaTabelaAtual < totalPaginas - 1) {
                paginaTabelaAtual++;
                setTimeout(proximoPassoCiclo, TEMPO_PAGINA_TABELA);
            } else {
                // Chegou na última página da tabela
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
                // Toca o item atual (pode ser Produto ou Propaganda)
                const item = dadosCache.playlist_final[indiceVideoAtual];
                mostrarOverlayVideo(item, () => {
                    // Quando acabar o vídeo:
                    indiceVideoAtual++;
                    proximoPassoCiclo();
                });
            } else {
                // Acabou a playlist
                if (configModo === 'MISTO') {
                    modoAtual = 'TABELA';
                    paginaTabelaAtual = 0;
                    esconderOverlayVideo();
                    proximoPassoCiclo();
                } else {
                    // Loop infinito nos vídeos
                    indiceVideoAtual = 0;
                    proximoPassoCiclo();
                }
            }
        }
    }

    // --- RENDERIZADOR DA TABELA ---
    function renderizarTabela(pagina) {
        esconderOverlayVideo(); 
        elConteudo.classList.add('fade'); 

        setTimeout(() => {
            elConteudo.innerHTML = ''; 
            
            const inicio = pagina * ITENS_POR_PAGINA;
            const fim = inicio + ITENS_POR_PAGINA;
            const produtosReais = dadosCache.produtos.slice(inicio, fim);
            
            const itensCol1 = [];
            const itensCol2 = [];

            // 1. Distribui produtos reais
            produtosReais.forEach((p, idx) => {
                if (idx < 9) itensCol1.push(criarItemHTML(p));
                else itensCol2.push(criarItemHTML(p));
            });

            // 2. Preenchimento de Espaços Vazios
            while (itensCol1.length < 9) itensCol1.push(criarItemVazio());
            while (itensCol2.length < 9) itensCol2.push(criarItemVazio());

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

    function criarItemHTML(produto) {
        const div = document.createElement('div');
        div.className = `item-produto ${produto.em_oferta ? 'em-oferta' : ''}`;
        
        const preco = parseFloat(produto.preco).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
        const nomeClass = produto.descricao.length > 23 ? 'nome-container marquee' : 'nome-container';

        div.innerHTML = `
            <div class="${nomeClass}"><span class="nome">${produto.descricao}</span></div>
            <div class="preco">${preco}</div>
        `;
        return div;
    }

    function criarItemVazio() {
        const div = document.createElement('div');
        div.className = 'item-produto';
        div.innerHTML = `
            <div class="nome-container"><span class="nome">&nbsp;</span></div>
            <div class="preco">&nbsp;</div>
        `;
        return div;
    }

    // --- RENDERIZADOR DE VÍDEO (OVERLAY) ---
    function mostrarOverlayVideo(item, onComplete) {
        
        elVideoContainer.innerHTML = '';
        elVideoContainer.style.display = 'block';

        // Detecta se é Produto ou Propaganda
        const isPropaganda = item.tipo === 'propaganda';
        const videoUrl = isPropaganda ? item.url : item.template_video.arquivo_video;

        // 1. Elemento de Vídeo
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

        // --- LÓGICA DE TEXTO (SÓ PARA PRODUTOS) ---
        const template = item.template_video;
        
        // Função auxiliar ajustada
        const createEl = (conteudo, top, left, styleBase, estilosExtras) => {
            if (estilosExtras && estilosExtras.display === 'none') return null;

            const el = document.createElement('div');
            el.className = 'overlay-element pop-in';
            
            if (conteudo.startsWith('<img')) el.innerHTML = conteudo;
            else el.innerText = conteudo;

            // Posição Base
            el.style.top = top + '%';
            el.style.left = left + '%';
            el.style.transform = `translate(-50%, -50%)`;

            // Mescla estilos
            const styleFinal = { ...styleBase, ...estilosExtras };
            
            // Aplica Fonte VH (Escala Real na TV)
            if (styleFinal.fontSizeVh) {
                el.style.fontSize = styleFinal.fontSizeVh + 'vh';
            } else if (styleFinal.fontSize) {
                // Fallback legado
                el.style.fontSize = styleFinal.fontSize;
            }
            
            // --- Lista Permissiva Incluindo WIDTH/HEIGHT ---
            const propsPermitidas = [
                'color', 'backgroundColor', 'fontFamily', 'fontWeight', 
                'fontStyle', 'textDecoration', 'width', 'height', 'zIndex'
            ];
            
            propsPermitidas.forEach(prop => {
                if(styleFinal[prop]) el.style[prop] = styleFinal[prop];
            });

            return el;
        };

        // Título
        const elTit = createEl(item.descricao, template.titulo_top, template.titulo_left, 
            { color: template.titulo_cor }, template.estilos_css['el-titulo']);
        if(elTit) elVideoContainer.appendChild(elTit);
        
        // Preço
        const precoVal = parseFloat(item.preco).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
        const elPreco = createEl(precoVal, template.preco_top, template.preco_left, 
            { color: template.preco_cor }, template.estilos_css['el-preco']);
        if(elPreco) elVideoContainer.appendChild(elPreco);

        // Imagem (Agora com Width sendo aplicado corretamente)
        if (item.imagem) {
            const imgHTML = `<img src="${item.imagem}" style="width:100%; height:100%; object-fit:contain;">`;
            const elImg = createEl(imgHTML, template.img_top, template.img_left, 
                { width: template.img_width + '%' }, template.estilos_css['el-imagem']);
            if(elImg) elVideoContainer.appendChild(elImg);
        }

        // Extras
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