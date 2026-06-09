/* ==========================================================================
                                BOOTSTRAP DA APLICAÇÃO
   ========================================================================== */

/**
 * Ponto de entrada da Single Page Application (SPA).
 * Inicializa a instância principal do TVApp assim que o DOM for carregado.
 */
document.addEventListener('DOMContentLoaded', () => {
    const app = new TVApp();
    app.init();
});


/* ==========================================================================
                                CONFIGURAÇÕES GERAIS
   ========================================================================== */

const CONFIG = {
    API_BASE: '/api/painel',
    UPDATE_INTERVAL_MS: 60000, 
    RETRY_DELAY_MS: 5000,      
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


/* ==========================================================================
                                CORE: CONTROLLER PRINCIPAL
   ========================================================================== */

class TVApp {
    /**
     * Gerencia o ciclo de vida da aplicação, estado do dispositivo e a 
     * orquestração entre a interface de pareamento e o player.
     */
    constructor() {
        this.elements = this._mapElements();
        this.state = {
            uuid: localStorage.getItem('tv_device_uuid'),
            data: null, 
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
        if (this.pollingInterval) clearInterval(this.pollingInterval);

        this.elements.SETUP_SCREEN.style.display = 'flex';
        this.elements.APP_SCREEN.style.display = 'none';
        
        if (this.elements.INPUT_UUID) {
            this.elements.INPUT_UUID.value = ""; 
            this.elements.INPUT_UUID.placeholder = "CÓDIGO DE 6 DÍGITOS";
            this.elements.INPUT_UUID.focus();
        }
    }

    async _startApp() {
        this.elements.SETUP_SCREEN.style.display = 'none';
        this.elements.APP_SCREEN.style.display = 'flex';
        
        await this._fetchData();
        
        if (this.pollingInterval) clearInterval(this.pollingInterval);
        this.pollingInterval = setInterval(() => this._fetchData(), CONFIG.UPDATE_INTERVAL_MS);
    }

    async _handlePairing() {
        const code = this.elements.INPUT_UUID.value.trim();
        if (code.length < 2) return alert("Por favor, informe um código de acesso válido.");

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
            console.error("Falha na sincronização de dados:", error);
            if (error.status === 404) {
                this._handleDeviceUnlinked();
            }
        }
    }

    _handleDeviceUnlinked() {
        console.warn("Sessão invalidada pelo servidor. Exigindo repareamento.");
        localStorage.removeItem('tv_device_uuid');
        this.state.uuid = null;
        this.state.data = null;
        this._showSetupScreen();
    }

    _processDataUpdate(newData) {
        this._updateOrientation(newData.config.orientacao);

        const newHash = JSON.stringify(newData.playlist_final);
        
        if (newHash !== this.state.playlistHash) {
            console.log("Mutação de playlist detectada. Reconstruindo fila de reprodução.");
            this.state.playlistHash = newHash;
            this.state.data = newData;
            this.playlistManager.updatePlaylist(newData.playlist_final, newData.produtos);
        } else {
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


/* ==========================================================================
                                GERENCIADOR DE PLAYLIST
   ========================================================================== */

class PlaylistManager {
    /**
     * Máquina de estados responsável pela iteração do array de mídia/tabelas.
     * Instancia os renderizadores adequados para cada tipo de nó da playlist.
     */
    constructor(app) {
        this.app = app;
        this.queue = [];
        this.products = [];
        this.currentIndex = 0;
        this.isPlaying = false; 
        this.timeoutId = null; 
        
        this.gridRenderer = new GridRenderer(app);
        this.videoPlayer = new VideoPlayer(app);
    }

    updatePlaylist(playlist, products) {
        const orderChanged = this.queue.length > 0 && JSON.stringify(this.queue) !== JSON.stringify(playlist);
        
        this.queue = playlist;
        this.products = products;
        
        if (orderChanged) {
            this.currentIndex = 0;
        }

        if (!this.isPlaying && this.queue.length > 0) {
            if (this.timeoutId) clearTimeout(this.timeoutId);
            this.playNext();
        }
    }

    updateCatalog(products) {
        this.products = products;
    }

    playNext() {
        if (!this.app.state.uuid) {
            this.isPlaying = false;
            return;
        }

        this.isPlaying = true;

        if (!this.queue || this.queue.length === 0) {
            this.isPlaying = false;
            this.app.setTitle("AGUARDANDO");
            this.app.getContainer().innerHTML = 
                "<h2 style='color:#666; text-align:center; margin-top:20vh;'>Aguardando configuração de playlist...</h2>";
            
            this.timeoutId = setTimeout(() => {
                if (!this.isPlaying) this.playNext();
            }, CONFIG.RETRY_DELAY_MS);
            return;
        }

        if (this.currentIndex >= this.queue.length) {
            this.currentIndex = 0;
        }

        const item = this.queue[this.currentIndex];
        this.currentIndex++;

        if (item.tipo === 'tabela') {
            this.gridRenderer.render(item, this.products, () => this.playNext());
        } else if (item.tipo === 'propaganda') {
            this.videoPlayer.play(item, () => this.playNext());
        } else {
            this.playNext(); 
        }
    }
}


/* ==========================================================================
                                ENGINE: RENDERIZADOR DE GRADE
   ========================================================================== */

class GridRenderer {
    /**
     * Responsável pela construção algorítmica do layout de tabelas de preço,
     * incluindo lógica de paginação e filtragem de visibilidade por item.
     */
    constructor(app) {
        this.app = app;
    }

    async render(itemPlaylist, allProducts, onComplete) {
        this.app.getVideoContainer().style.display = 'none';
        this.app.getVideoContainer().innerHTML = '';

        const titulo = itemPlaylist.descricao ? itemPlaylist.descricao.replace('Tabela: ', '').toUpperCase() : '';
        const container = this.app.getContainer();
        
        container.style.opacity = '0';
        await new Promise(r => setTimeout(r, 300));

        this.app.setTitle(titulo);

        // 1. FILTRO GLOBAL: Remove produtos ocultados na página de Produtos
        let productsToShow = allProducts.filter(p => p.exibir_no_painel === true);

        if (itemPlaylist.produtos_ordenados && Array.isArray(itemPlaylist.produtos_ordenados)) {
            // RENDERIZAÇÃO DE LISTA PERSONALIZADA
            // Mapeia estritamente os IDs na ordem definida, ignorando filtros de família e ocultos locais
            const orderedIds = itemPlaylist.produtos_ordenados.map(String);
            productsToShow = orderedIds
                .map(id => productsToShow.find(p => String(p.id) === id))
                .filter(p => p !== undefined); // Remove se algum produto da lista foi apagado
                
        } else {
            // RENDERIZAÇÃO TRADICIONAL (POR FAMÍLIA)
            // 2. FILTRO DE FAMÍLIA: Aplica a categoria selecionada na Playlist
            if (itemPlaylist.familia_id) {
                productsToShow = productsToShow.filter(p => p.familia === itemPlaylist.familia_id);
            }

            // 3. FILTRO LOCAL (BLINDAGEM DA TV): Remove produtos ocultados especificamente nesta Playlist
            if (itemPlaylist.hidden_products && Array.isArray(itemPlaylist.hidden_products)) {
                const hiddenIds = itemPlaylist.hidden_products.map(String);
                
                productsToShow = productsToShow.filter(p => {
                    const productId = String(p.id);
                    return !hiddenIds.includes(productId);
                });
            }
        }

        if (productsToShow.length === 0) {
            container.innerHTML = "<h2 style='text-align:center; color:#666; width:100%; margin-top:20vh;'>Nenhum produto indexado para exibição.</h2>";
            container.style.opacity = '1';
            setTimeout(onComplete, 3000);
            return;
        }

        await this._paginate(productsToShow, itemPlaylist.tempo_pagina || 15, onComplete);
    }

    async _paginate(products, durationSec, onComplete) {
        const itemsPerPage = this.app.isVertical() ? CONFIG.ITEMS_PER_PAGE.VERTICAL : CONFIG.ITEMS_PER_PAGE.HORIZONTAL;
        const totalPages = Math.ceil(products.length / itemsPerPage);

        for (let i = 0; i < totalPages; i++) {
            if (!this.app.state.uuid) return onComplete();

            const start = i * itemsPerPage;
            const pageProducts = products.slice(start, start + itemsPerPage);
            
            await this._drawPage(pageProducts, itemsPerPage);
            await new Promise(r => setTimeout(r, durationSec * 1000));
        }

        this.app.getContainer().style.opacity = '0';
        await new Promise(r => setTimeout(r, 300));
        
        onComplete();
    }

    async _drawPage(products, itemsPerPage) {
        const container = this.app.getContainer();
        
        container.style.opacity = '0';
        await new Promise(r => setTimeout(r, 400));
        
        container.innerHTML = '';
        if (this.app.isVertical()) {
            container.appendChild(this._createColumn(products, itemsPerPage));
        } else {
            const itemsPerCol = Math.ceil(itemsPerPage / 2);
            container.appendChild(this._createColumn(products.slice(0, itemsPerCol), itemsPerCol));
            container.appendChild(this._createColumn(products.slice(itemsPerCol), itemsPerCol));
        }
        
        container.style.opacity = '1';
        await new Promise(r => setTimeout(r, 400));
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
        
        div.innerHTML = `<div class="${nameClass}"><span class="nome">${product.descricao}</span></div><div class="preco">${priceFormatted}</div>`;
        return div;
    }

    _createEmptyCard() {
        const div = document.createElement('div');
        div.className = 'item-produto';
        div.innerHTML = `<div class="nome-container"><span class="nome">&nbsp;</span></div><div class="preco">&nbsp;</div>`;
        return div;
    }
}


/* ==========================================================================
                                ENGINE: RENDERIZADOR DE MÍDIA
   ========================================================================== */

class VideoPlayer {
    /**
     * Manipula a injeção e ciclo de vida de nós de imagem/vídeo no DOM.
     * 
     * Implementa múltiplas camadas de proteção contra falhas silenciosas em Smart TVs
     * (WebOS/Tizen/Android TV), que frequentemente:
     *  - Não disparam `onerror` em broken pipe — apenas travam silenciosamente
     *  - Rejeitam `video.play()` via Promise se a política de autoplay bloqueia
     *  - Emitem `onstalled` / `onsuspend` quando o buffer congela
     *  - Não suportam Range Requests (resolvido pelo media_stream_view no backend)
     */
    constructor(app) {
        this.app = app;
        this._stallCount = 0;
    }

    play(item, onComplete) {
        if (!this.app.state.uuid || !item.url) {
            console.warn('[VideoPlayer] Item inválido ou sem URL. Avançando playlist.');
            onComplete();
            return;
        }

        const container = this.app.getVideoContainer();
        container.innerHTML = '';
        container.style.opacity = '0';
        container.style.display = 'block';

        const durationMs = (item.duracao || 15) * 1000;
        let isFinished = false;
        let safetyTimeout = null;
        let stallTimeout = null;
        let loadTimeout = null;

        const finish = async (reason) => {
            if (isFinished) return;
            isFinished = true;

            // Limpa todos os timers pendentes
            if (safetyTimeout) clearTimeout(safetyTimeout);
            if (stallTimeout) clearTimeout(stallTimeout);
            if (loadTimeout) clearTimeout(loadTimeout);

            console.log(`[VideoPlayer] Finalizando: "${item.descricao}" (motivo: ${reason})`);

            container.style.opacity = '0';
            await new Promise(r => setTimeout(r, 400));

            // Para e destroi o elemento de vídeo antes de limpar o DOM
            const vid = container.querySelector('video');
            if (vid) {
                vid.pause();
                vid.removeAttribute('src');
                vid.load();
            }

            container.style.display = 'none';
            container.innerHTML = '';
            onComplete();
        };

        // Fade-in suave
        setTimeout(() => {
            if (!isFinished) container.style.opacity = '1';
        }, 100);

        if (item.tipo_midia === 'IMAGEM') {
            // --- PLAYER DE IMAGEM ---
            const img = document.createElement('img');
            img.id = 'video-bg';
            img.src = item.url;
            img.onerror = () => finish('image-error');
            safetyTimeout = setTimeout(() => finish('image-duration'), durationMs);
            container.appendChild(img);

        } else {
            // --- PLAYER DE VÍDEO ---
            const video = document.createElement('video');
            video.id = 'video-bg';

            // Atributos mandatórios para autoplay em engines de TV restritivas (Tizen/WebOS)
            video.setAttribute('muted', 'true');
            video.setAttribute('autoplay', 'true');
            video.setAttribute('playsinline', 'true');
            video.setAttribute('preload', 'auto');
            video.muted = true;
            video.autoplay = true;

            // Quando o vídeo termina naturalmente → avança imediatamente
            video.onended = () => finish('video-ended');

            // Erro de decodificação / URL inválida → avança
            video.onerror = (e) => {
                console.error('[VideoPlayer] Erro no elemento <video>:', e, video.error);
                finish('video-error');
            };

            // Timeout de carregamento inicial: se não iniciar reprodução em 8s, desiste.
            // TVs lentas podem demorar no primeiro buffer, então usamos 8s de tolerância.
            loadTimeout = setTimeout(() => {
                if (!isFinished && video.readyState < 3) { // < HAVE_FUTURE_DATA
                    console.warn('[VideoPlayer] Timeout de carregamento inicial. URL:', item.url);
                    finish('load-timeout');
                }
            }, 8000);

            // Quando começar a reproduzir: cancela o loadTimeout e arma o safetyTimeout
            video.oncanplay = () => {
                if (loadTimeout) { clearTimeout(loadTimeout); loadTimeout = null; }
                // Safety timeout: garante avanço mesmo se onended não disparar
                if (!safetyTimeout) {
                    safetyTimeout = setTimeout(() => finish('safety-duration'), durationMs + 3000);
                }
            };

            // Detecta buffer travado (stalled) — comum em TVs Android e WebOS
            const handleStall = () => {
                if (isFinished) return;
                // Dá 5s de tolerância para o buffer se recuperar antes de desistir
                if (stallTimeout) clearTimeout(stallTimeout);
                stallTimeout = setTimeout(() => {
                    if (!isFinished && video.paused) {
                        console.warn('[VideoPlayer] Buffer travado e vídeo pausado. Tentando retomar...');
                        video.play().catch(() => finish('stall-unrecoverable'));
                    }
                }, 5000);
            };

            video.onstalled = handleStall;
            video.onsuspend = () => {
                // onsuspend também pode indicar que o browser parou o download
                if (!isFinished && video.readyState < 2) handleStall();
            };

            // Safety timeout de emergência: garante que a playlist SEMPRE avança
            // Ativado imediatamente como última barreira — usando duracao + 15s de buffer total
            safetyTimeout = setTimeout(() => finish('emergency-timeout'), durationMs + 15000);

            container.appendChild(video);

            // Injeta a URL e força o carregamento
            video.src = item.url;
            video.load();

            // Tenta reproduzir. Em TVs, play() retorna uma Promise que pode ser rejeitada.
            const playPromise = video.play();
            if (playPromise !== undefined) {
                playPromise.catch(err => {
                    console.warn('[VideoPlayer] video.play() rejeitado:', err.message);
                    // Se a política de autoplay bloqueou, tenta silenciosamente com muted
                    if (!isFinished) {
                        video.muted = true;
                        video.play().catch(() => finish('autoplay-blocked'));
                    }
                });
            }
        }
    }
}


/* ==========================================================================
                                CLIENTE HTTP (API)
   ========================================================================== */

const API = {
    /**
     * Wrapper estático para requisições de pareamento e pull de estado via Fetch API.
     */
    async pairDevice(code) {
        const response = await fetch(`${CONFIG.API_BASE}/parear/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ codigo: code })
        });

        if (!response.ok) {
            let msg = "Erro desconhecido de integração.";
            try { 
                const json = await response.json(); 
                msg = json.erro || msg; 
            } catch(e) {}
            throw new Error(msg);
        }
        return await response.json();
    },

    async getPanelData(uuid) {
        const response = await fetch(`${CONFIG.API_BASE}/${uuid}/`);
        if (!response.ok) {
            const error = new Error(`Falha de comunicação: Status HTTP ${response.status}`);
            error.status = response.status;
            throw error;
        }
        return await response.json();
    }
};