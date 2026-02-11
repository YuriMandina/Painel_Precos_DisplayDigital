/**
 * TV App - Display Digital
 * Responsável por gerenciar a reprodução de conteúdo (Playlist, Vídeos e Tabelas de Preço).
 */

document.addEventListener('DOMContentLoaded', () => {
    // Inicializa a aplicação
    const app = new TVApp();
    app.init();
});

// --- CONSTANTES & CONFIGURAÇÃO ---
const CONFIG = {
    API_BASE: '/api/painel',
    UPDATE_INTERVAL_MS: 60000, // 1 minuto
    RETRY_DELAY_MS: 5000,      // 5 segundos
    DEFAULT_DURATION_MS: 15000,
    ITEMS_PER_PAGE: {
        HORIZONTAL: 18,
        VERTICAL: 15
    },
    SELECTORS: {
        SETUP_SCREEN: 'setup-screen',
        APP_SCREEN: 'app-screen',
        INPUT_UUID: 'input-uuid',
        BTN_SAVE: 'btn-salvar',
        TITLE: 'titulo-painel',
        CONTENT: 'painel-conteudo',
        VIDEO_CONTAINER: 'video-overlay-container'
    }
};

// --- CLASSE PRINCIPAL ---
class TVApp {
    constructor() {
        this.elements = this._mapElements();
        this.state = {
            uuid: localStorage.getItem('tv_device_uuid'),
            data: null, // Dados completos da API
            orientation: 'HORIZONTAL',
            playlistHash: ''
        };
        
        this.playlistManager = new PlaylistManager(this);
        this.pollingInterval = null;
    }

    _mapElements() {
        const els = {};
        for (const [key, id] of Object.entries(CONFIG.SELECTORS)) {
            els[key] = document.getElementById(id);
        }
        return els;
    }

    init() {
        this._setupEventListeners();

        if (!this.state.uuid) {
            this._showSetupScreen();
        } else {
            this._startApp();
        }
    }

    _setupEventListeners() {
        if (this.elements.BTN_SAVE) {
            this.elements.BTN_SAVE.addEventListener('click', () => this._handlePairing());
        }
    }

    _showSetupScreen() {
        // Para qualquer polling anterior para evitar chamadas fantasmas
        if (this.pollingInterval) clearInterval(this.pollingInterval);

        this.elements.SETUP_SCREEN.style.display = 'flex';
        this.elements.APP_SCREEN.style.display = 'none';
        
        if (this.elements.INPUT_UUID) {
            this.elements.INPUT_UUID.value = ""; // Limpa input anterior
            this.elements.INPUT_UUID.placeholder = "CÓDIGO DE 6 DÍGITOS";
            this.elements.INPUT_UUID.focus();
        }
    }

    _startApp() {
        this.elements.SETUP_SCREEN.style.display = 'none';
        this.elements.APP_SCREEN.style.display = 'flex';
        
        // Carga inicial
        this._fetchData();
        
        // Polling de atualização de dados
        if (this.pollingInterval) clearInterval(this.pollingInterval);
        this.pollingInterval = setInterval(() => this._fetchData(), CONFIG.UPDATE_INTERVAL_MS);
        
        // Inicia o loop da playlist
        this.playlistManager.playNext();
    }

    async _handlePairing() {
        const code = this.elements.INPUT_UUID.value.trim();
        if (code.length < 2) return alert("Por favor, digite o código exibido no painel.");

        try {
            const data = await API.pairDevice(code);
            localStorage.setItem('tv_device_uuid', data.uuid);
            this.state.uuid = data.uuid;
            this._startApp();
        } catch (error) {
            alert(error.message);
        }
    }

    async _fetchData() {
        if (!this.state.uuid) return;

        try {
            const data = await API.getPanelData(this.state.uuid);
            this._processDataUpdate(data);
        } catch (error) {
            console.error("Erro ao atualizar dados:", error);
            
            // Correção: Se a API retornar 404, o dispositivo foi deletado no servidor.
            // Devemos resetar o estado local para permitir novo pareamento.
            if (error.status === 404) {
                this._handleDeviceUnlinked();
            }
        }
    }

    _handleDeviceUnlinked() {
        console.warn("Dispositivo não reconhecido pelo servidor. Reiniciando pareamento.");
        localStorage.removeItem('tv_device_uuid');
        this.state.uuid = null;
        this.state.data = null;
        this._showSetupScreen();
    }

    _processDataUpdate(newData) {
        // 1. Detecta Mudança de Orientação
        this._updateOrientation(newData.config.orientacao);

        // 2. Verifica se a Playlist mudou (usando Hash simples)
        const newHash = JSON.stringify(newData.playlist_final.map(i => i.tipo + i.id));
        
        if (newHash !== this.state.playlistHash) {
            console.log("Nova playlist detectada. Itens:", newData.playlist_final.length);
            this.state.playlistHash = newHash;
            this.state.data = newData;
            this.playlistManager.updatePlaylist(newData.playlist_final, newData.produtos);
        } else {
            // Apenas atualiza o catálogo de produtos caso preços mudem, sem resetar playlist
            this.playlistManager.updateCatalog(newData.produtos);
        }
    }

    _updateOrientation(orientation) {
        if (this.state.orientation === orientation) return;

        document.body.classList.remove('rotacao-90', 'rotacao-270');
        this.elements.CONTENT.classList.remove('layout-vertical');

        if (orientation === 'VERTICAL_DIR') {
            document.body.classList.add('rotacao-90');
            this.elements.CONTENT.classList.add('layout-vertical');
        } else if (orientation === 'VERTICAL_ESQ') {
            document.body.classList.add('rotacao-270');
            this.elements.CONTENT.classList.add('layout-vertical');
        }

        this.state.orientation = orientation;
    }

    // Métodos de UI expostos para os Managers
    setTitle(text) {
        if (this.elements.TITLE) this.elements.TITLE.innerText = text || "";
    }

    getContainer() {
        return this.elements.CONTENT;
    }

    getVideoContainer() {
        return this.elements.VIDEO_CONTAINER;
    }

    isVertical() {
        return this.state.orientation.includes('VERTICAL');
    }
}

// --- GERENCIADOR DE PLAYLIST ---
class PlaylistManager {
    constructor(app) {
        this.app = app;
        this.queue = [];
        this.products = [];
        this.currentIndex = 0;
        this.isPlaying = false; // Flag para evitar múltiplas execuções simultâneas
        
        this.gridRenderer = new GridRenderer(app);
        this.videoPlayer = new VideoPlayer(app);
    }

    updatePlaylist(playlist, products) {
        this.queue = playlist;
        this.products = products;
        
        // Se a playlist estava vazia e agora tem itens, inicia
        if (!this.isPlaying && this.queue.length > 0) {
            this.playNext();
        }
    }

    updateCatalog(products) {
        this.products = products;
    }

    playNext() {
        // Se o UUID foi removido (despareamento), para o loop
        if (!this.app.state.uuid) {
            this.isPlaying = false;
            return;
        }

        this.isPlaying = true;

        if (!this.queue || this.queue.length === 0) {
            this.app.setTitle("AGUARDANDO");
            this.app.getContainer().innerHTML = 
                "<h2 style='color:#666; text-align:center; margin-top:20vh;'>Aguardando configuração...</h2>";
            
            // Tenta novamente em breve
            setTimeout(() => this.playNext(), CONFIG.RETRY_DELAY_MS);
            return;
        }

        if (this.currentIndex >= this.queue.length) {
            this.currentIndex = 0;
        }

        const item = this.queue[this.currentIndex];
        this.currentIndex++;

        // console.log(`Reproduzindo [${item.tipo}]: ${item.descricao}`);

        if (item.tipo === 'tabela') {
            this.gridRenderer.render(item, this.products, () => this.playNext());
        } else if (item.tipo === 'propaganda' || item.tipo === 'produto_video') {
            this.videoPlayer.play(item, () => this.playNext());
        } else {
            // Tipo desconhecido, pula
            this.playNext();
        }
    }
}

// --- RENDERIZADOR DE GRADE (TABELA) ---
class GridRenderer {
    constructor(app) {
        this.app = app;
    }

    render(itemPlaylist, allProducts, onComplete) {
        this.app.getVideoContainer().style.display = 'none';
        this.app.getVideoContainer().innerHTML = '';

        // Atualiza Título
        const titulo = itemPlaylist.descricao ? itemPlaylist.descricao.replace('Tabela: ', '').toUpperCase() : '';
        this.app.setTitle(titulo);

        // Filtra produtos da família
        let productsToShow = allProducts;
        if (itemPlaylist.familia_id) {
            productsToShow = allProducts.filter(p => p.familia === itemPlaylist.familia_id);
        }

        if (productsToShow.length === 0) {
            this.app.getContainer().innerHTML = "<h2 style='text-align:center; color:#666;'>Nenhum produto nesta categoria.</h2>";
            setTimeout(onComplete, 3000);
            return;
        }

        this._paginate(productsToShow, itemPlaylist.tempo_pagina || 15, onComplete);
    }

    _paginate(products, durationSec, onComplete) {
        // Verifica se o app ainda está pareado antes de continuar paginação
        if (!this.app.state.uuid) {
            onComplete();
            return;
        }

        const itemsPerPage = this.app.isVertical() ? CONFIG.ITEMS_PER_PAGE.VERTICAL : CONFIG.ITEMS_PER_PAGE.HORIZONTAL;
        const totalPages = Math.ceil(products.length / itemsPerPage);
        let currentPage = 0;

        const showPage = () => {
            // Checagem de segurança se despareou durante a transição
            if (!this.app.state.uuid) return;

            if (currentPage >= totalPages) {
                onComplete();
                return;
            }

            const start = currentPage * itemsPerPage;
            const pageProducts = products.slice(start, start + itemsPerPage);
            
            this._drawPage(pageProducts, itemsPerPage);
            currentPage++;

            setTimeout(showPage, durationSec * 1000);
        };

        showPage();
    }

    _drawPage(products, itemsPerPage) {
        const container = this.app.getContainer();
        container.classList.add('fade');

        setTimeout(() => {
            container.innerHTML = '';
            
            if (this.app.isVertical()) {
                const col = this._createColumn(products, itemsPerPage);
                container.appendChild(col);
            } else {
                const itemsPerCol = Math.ceil(itemsPerPage / 2);
                const col1 = this._createColumn(products.slice(0, itemsPerCol), itemsPerCol);
                const col2 = this._createColumn(products.slice(itemsPerCol), itemsPerCol);
                
                container.appendChild(col1);
                container.appendChild(col2);
            }
            container.classList.remove('fade');
        }, 300);
    }

    _createColumn(products, capacity) {
        const col = document.createElement('div');
        col.className = 'coluna';
        
        products.forEach(p => col.appendChild(this._createCard(p)));
        
        while (col.children.length < capacity) {
            col.appendChild(this._createEmptyCard());
        }
        return col;
    }

    _createCard(product) {
        const div = document.createElement('div');
        div.className = `item-produto ${product.em_oferta ? 'em-oferta' : ''}`;
        
        const priceFormatted = parseFloat(product.preco).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
        const charLimit = this.app.isVertical() ? 28 : 22;
        const nameClass = product.descricao.length > charLimit ? 'nome-container marquee' : 'nome-container';

        div.innerHTML = `
            <div class="${nameClass}"><span class="nome">${product.descricao}</span></div>
            <div class="preco">${priceFormatted}</div>
        `;
        return div;
    }

    _createEmptyCard() {
        const div = document.createElement('div');
        div.className = 'item-produto';
        div.innerHTML = `<div class="nome-container"><span class="nome">&nbsp;</span></div><div class="preco">&nbsp;</div>`;
        return div;
    }
}

// --- REPRODUTOR DE VÍDEO (OVERLAY) ---
class VideoPlayer {
    constructor(app) {
        this.app = app;
    }

    play(item, onComplete) {
        // Verifica se despareou
        if (!this.app.state.uuid) {
            onComplete();
            return;
        }

        const container = this.app.getVideoContainer();
        container.innerHTML = '';
        container.style.display = 'block';

        const isPropaganda = item.tipo === 'propaganda';
        let videoUrl = isPropaganda ? item.url : (item.template_video?.arquivo_video);

        if (!videoUrl) {
            onComplete();
            return;
        }

        const video = document.createElement('video');
        video.id = 'video-bg';
        video.src = videoUrl;
        video.muted = true;
        video.autoplay = true;
        video.playsInline = true;

        const durationMs = (item.duracao || 15) * 1000;
        const safetyTimeout = setTimeout(onComplete, durationMs + 1000);

        const finish = () => {
            clearTimeout(safetyTimeout);
            onComplete();
        };

        video.onerror = finish;
        video.onended = finish;

        container.appendChild(video);

        if (!isPropaganda && item.template_video) {
            this._renderOverlay(item);
        }
    }

    _renderOverlay(item) {
        const template = item.template_video;
        const css = template.estilos_css || {};
        const container = this.app.getVideoContainer();

        const createEl = (content, top, left, baseStyle, extraStyle) => {
            if (extraStyle && extraStyle.display === 'none') return;

            const el = document.createElement('div');
            el.className = 'overlay-element pop-in';
            
            if (typeof content === 'string' && content.trim().startsWith('<img')) {
                el.innerHTML = content;
            } else {
                el.innerText = content;
            }

            el.style.top = top + '%';
            el.style.left = left + '%';
            el.style.transform = `translate(-50%, -50%)`;

            const styles = { ...baseStyle, ...extraStyle };
            
            if (styles.fontSizeVh) el.style.fontSize = styles.fontSizeVh + 'vh';
            else if (styles.fontSize) el.style.fontSize = styles.fontSize;

            ['color', 'backgroundColor', 'fontFamily', 'fontWeight', 
             'fontStyle', 'textDecoration', 'width', 'height', 'zIndex'].forEach(prop => {
                if(styles[prop]) el.style[prop] = styles[prop];
            });

            container.appendChild(el);
        };

        createEl(item.descricao, template.titulo_top, template.titulo_left, { color: template.titulo_cor }, css['el-titulo']);
        
        const priceVal = parseFloat(item.preco).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
        createEl(priceVal, template.preco_top, template.preco_left, { color: template.preco_cor }, css['el-preco']);

        if (item.imagem) {
            const imgHTML = `<img src="${item.imagem}" style="width:100%; height:100%; object-fit:contain;">`;
            createEl(imgHTML, template.img_top, template.img_left, { width: template.img_width + '%' }, css['el-imagem']);
        }

        if (template.elementos_extras) {
            template.elementos_extras.forEach(extra => {
                createEl(extra.texto, extra.top, extra.left, {}, extra.style);
            });
        }
    }
}

// --- API CLIENT ---
const API = {
    async pairDevice(code) {
        const response = await fetch(`${CONFIG.API_BASE}/parear/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ codigo: code })
        });

        if (!response.ok) {
            let msg = "Erro desconhecido";
            try { const json = await response.json(); msg = json.erro || msg; } catch(e){}
            throw new Error(msg);
        }
        return await response.json();
    },

    async getPanelData(uuid) {
        const response = await fetch(`${CONFIG.API_BASE}/${uuid}/`);
        if (!response.ok) {
            // Correção: Lança um objeto de erro com o status para tratamento no Controller
            const error = new Error(`Erro API: ${response.status}`);
            error.status = response.status;
            throw error;
        }
        return await response.json();
    }
};