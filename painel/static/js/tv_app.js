/* ==========================================================================
                                BOOTSTRAP DA APLICAÇÃO
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    const app = new TVApp();
    app.init();
});

const CONFIG = {
    API_BASE: '/api/painel',
    UPDATE_INTERVAL_MS: 60000,
    RETRY_DELAY_MS: 5000,
    DEFAULT_DURATION_MS: 15000,
    ITEMS_PER_PAGE: {
        HORIZONTAL: 18,
        VERTICAL: 14
    },
    SELECTORS: {
        SETUP_SCREEN: 'setup-screen',
        APP_SCREEN: 'app-screen',
        INPUT_UUID: 'input-uuid',
        BTN_SAVE: 'btn-salvar'
    }
};

class TVApp {
    constructor() {
        this.elements = this._mapElements();
        this.state = {
            uuid: localStorage.getItem('tv_device_uuid'),
            data: null,
            orientation: 'HORIZONTAL',
            playlistHash: ''
        };

        this.managers = {};
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
            
            // Stop existing managers
            Object.values(this.managers).forEach(m => m.stop());
            this.managers = {};

            if (newData.playlist_final && newData.playlist_final.layout === 'split_asimetrico') {
                document.getElementById('zone-single').style.display = 'none';
                document.getElementById('zone-split').style.display = 'flex';
                
                this.managers.left = new PlaylistManager(this, 'left');
                this.managers.right = new PlaylistManager(this, 'right');
                
                this.managers.left.updatePlaylist(newData.playlist_final.zones.left || [], newData.produtos);
                this.managers.right.updatePlaylist(newData.playlist_final.zones.right || [], newData.produtos);
                
                this._adjustSplitWidths(newData.playlist_final.zones);
            } else {
                document.getElementById('zone-split').style.display = 'none';
                document.getElementById('zone-single').style.display = 'block';
                
                this.managers.single = new PlaylistManager(this, 'single');
                this.managers.single.updatePlaylist(newData.playlist_final || [], newData.produtos);
            }

        } else {
            Object.values(this.managers).forEach(m => m.updateCatalog(newData.produtos));
        }
    }

    _adjustSplitWidths(zones) {
        const leftHasMedia = zones.left && zones.left.some(i => i.tipo === 'propaganda');
        const rightHasMedia = zones.right && zones.right.some(i => i.tipo === 'propaganda');
        const leftHasTable = zones.left && zones.left.some(i => i.tipo === 'tabela');
        const rightHasTable = zones.right && zones.right.some(i => i.tipo === 'tabela');
        
        const zoneLeft = document.getElementById('zone-left');
        const zoneRight = document.getElementById('zone-right');
        
        if (leftHasMedia && !leftHasTable && rightHasTable) {
            zoneLeft.style.flex = "0 0 31.64%";
            zoneRight.style.flex = "1";
        } else if (rightHasMedia && !rightHasTable && leftHasTable) {
            zoneRight.style.flex = "0 0 31.64%";
            zoneLeft.style.flex = "1";
        } else {
            zoneLeft.style.flex = "1";
            zoneRight.style.flex = "1";
        }
    }

    _updateOrientation(orientation) {
        if (this.state.orientation === orientation) return;

        document.body.classList.remove('rotacao-90', 'rotacao-270');
        document.querySelectorAll('.painel-conteudo').forEach(el => el.classList.remove('layout-vertical'));

        if (orientation === 'VERTICAL_DIR') {
            document.body.classList.add('rotacao-90');
            document.querySelectorAll('.painel-conteudo').forEach(el => el.classList.add('layout-vertical'));
        } else if (orientation === 'VERTICAL_ESQ') {
            document.body.classList.add('rotacao-270');
            document.querySelectorAll('.painel-conteudo').forEach(el => el.classList.add('layout-vertical'));
        }

        this.state.orientation = orientation;
    }

    setTitle(text, zoneId = 'single') {
        let elId = 'titulo-painel';
        if (zoneId === 'left') elId = 'titulo-painel-left';
        if (zoneId === 'right') elId = 'titulo-painel-right';
        const el = document.getElementById(elId);
        if (el) el.innerText = text || "";
    }

    getContainer(zoneId = 'single') {
        if (zoneId === 'left') return document.getElementById('painel-conteudo-left');
        if (zoneId === 'right') return document.getElementById('painel-conteudo-right');
        return document.getElementById('painel-conteudo');
    }

    getVideoContainer(zoneId = 'single') {
        if (zoneId === 'left') return document.getElementById('video-overlay-container-left');
        if (zoneId === 'right') return document.getElementById('video-overlay-container-right');
        return document.getElementById('video-overlay-container');
    }

    isVertical() {
        return this.state.orientation.includes('VERTICAL');
    }
}

class PlaylistManager {
    constructor(app, zoneId) {
        this.app = app;
        this.zoneId = zoneId;
        this.queue = [];
        this.products = [];
        this.currentIndex = 0;
        this.isPlaying = false;
        this.timeoutId = null;

        this.gridRenderer = new GridRenderer(app, zoneId);
        this.videoPlayer = new VideoPlayer(app, zoneId);
        
        this.isStopped = false;
    }
    
    stop() {
        this.isStopped = true;
        this.isPlaying = false;
        if (this.timeoutId) clearTimeout(this.timeoutId);
        this.gridRenderer.stop();
        this.videoPlayer.stop();
    }

    updatePlaylist(playlist, products) {
        if (this.isStopped) return;
        const orderChanged = this.queue.length > 0 && JSON.stringify(this.queue) !== JSON.stringify(playlist);
        this.queue = playlist;
        this.products = products;

        if (orderChanged) this.currentIndex = 0;

        if (!this.isPlaying && this.queue.length > 0) {
            if (this.timeoutId) clearTimeout(this.timeoutId);
            this.playNext();
        }
    }

    updateCatalog(products) {
        if (this.isStopped) return;
        this.products = products;
    }

    playNext() {
        if (this.isStopped) return;
        if (!this.app.state.uuid) {
            this.isPlaying = false;
            return;
        }

        this.isPlaying = true;

        if (!this.queue || this.queue.length === 0) {
            this.isPlaying = false;
            this.app.setTitle("AGUARDANDO", this.zoneId);
            this.app.getContainer(this.zoneId).innerHTML =
                "<h2 style='color:#666; text-align:center; margin-top:20vh; width:100%;'>Aguardando configuração de playlist...</h2>";

            this.timeoutId = setTimeout(() => {
                if (!this.isPlaying && !this.isStopped) this.playNext();
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

class GridRenderer {
    constructor(app, zoneId) {
        this.app = app;
        this.zoneId = zoneId;
        this.isStopped = false;
        this.currentTimeout = null;
    }
    
    stop() {
        this.isStopped = true;
        if (this.currentTimeout) clearTimeout(this.currentTimeout);
    }

    async render(itemPlaylist, allProducts, onComplete) {
        if (this.isStopped) return;
        const titulo = itemPlaylist.descricao ? itemPlaylist.descricao.replace('Tabela: ', '').toUpperCase() : '';
        const container = this.app.getContainer(this.zoneId);

        container.style.opacity = '0';
        await new Promise(r => { this.currentTimeout = setTimeout(r, 300); });
        if (this.isStopped) return;

        this.app.setTitle(titulo, this.zoneId);

        let productsToShow = allProducts.filter(p => p.exibir_no_painel === true);

        if (itemPlaylist.produtos_ordenados && Array.isArray(itemPlaylist.produtos_ordenados)) {
            const orderedIds = itemPlaylist.produtos_ordenados.map(String);
            productsToShow = orderedIds
                .map(id => productsToShow.find(p => String(p.id) === id))
                .filter(p => p !== undefined);
        } else {
            if (itemPlaylist.familia_id) {
                productsToShow = productsToShow.filter(p => p.familia === itemPlaylist.familia_id);
            }
            if (itemPlaylist.hidden_products && Array.isArray(itemPlaylist.hidden_products)) {
                const hiddenIds = itemPlaylist.hidden_products.map(String);
                productsToShow = productsToShow.filter(p => !hiddenIds.includes(String(p.id)));
            }
        }

        if (productsToShow.length === 0) {
            container.innerHTML = "<h2 style='text-align:center; color:#666; width:100%; margin-top:20vh;'>Nenhum produto indexado para exibição.</h2>";
            container.style.opacity = '1';
            this._hideVideoOverlay();
            this.currentTimeout = setTimeout(() => { if (!this.isStopped) onComplete(); }, 3000);
            return;
        }

        await this._paginate(productsToShow, itemPlaylist.tempo_pagina || 15, onComplete);
    }

    async _paginate(products, durationSec, onComplete) {
        let itemsPerPage = this.app.isVertical() ? CONFIG.ITEMS_PER_PAGE.VERTICAL : CONFIG.ITEMS_PER_PAGE.HORIZONTAL;
        if (!this.app.isVertical() && this.zoneId !== 'single') {
            itemsPerPage = Math.ceil(itemsPerPage / 2);
        }
        const totalPages = Math.ceil(products.length / itemsPerPage);

        for (let i = 0; i < totalPages; i++) {
            if (!this.app.state.uuid || this.isStopped) return;

            const start = i * itemsPerPage;
            const pageProducts = products.slice(start, start + itemsPerPage);

            await this._drawPage(pageProducts, itemsPerPage);
            if (this.isStopped) return;
            
            await new Promise(r => { this.currentTimeout = setTimeout(r, durationSec * 1000); });
            if (this.isStopped) return;
        }

        this.app.getContainer(this.zoneId).style.opacity = '0';
        await new Promise(r => { this.currentTimeout = setTimeout(r, 300); });
        if (this.isStopped) return;

        onComplete();
    }

    _hideVideoOverlay() {
        const videoContainer = this.app.getVideoContainer(this.zoneId);
        if (videoContainer.style.display !== 'none' && videoContainer.style.opacity !== '0') {
            videoContainer.style.opacity = '0';
            setTimeout(() => {
                if (this.isStopped) return;
                Array.from(videoContainer.children).forEach(child => {
                    if (child.tagName === 'VIDEO') {
                        child.pause();
                        child.removeAttribute('src');
                        child.load();
                    }
                });
                videoContainer.innerHTML = '';
                videoContainer.style.display = 'none';
            }, 400);
        }
    }

    async _drawPage(products, itemsPerPage) {
        const container = this.app.getContainer(this.zoneId);

        container.style.opacity = '0';
        await new Promise(r => { this.currentTimeout = setTimeout(r, 400); });
        if (this.isStopped) return;

        container.innerHTML = '';
        if (this.app.isVertical() || this.zoneId !== 'single') {
            container.classList.add('layout-single-column');
            container.appendChild(this._createColumn(products, itemsPerPage));
        } else {
            container.classList.remove('layout-single-column');
            const itemsPerCol = Math.ceil(itemsPerPage / 2);
            container.appendChild(this._createColumn(products.slice(0, itemsPerCol), itemsPerCol));
            container.appendChild(this._createColumn(products.slice(itemsPerCol), itemsPerCol));
        }

        container.style.opacity = '1';
        this._hideVideoOverlay();
        await new Promise(r => { this.currentTimeout = setTimeout(r, 400); });
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

        const priceFormatted = parseFloat(product.preco).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
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

class VideoPlayer {
    constructor(app, zoneId) {
        this.app = app;
        this.zoneId = zoneId;
        this.isStopped = false;
        this._stallCount = 0;
        this.timeouts = [];
    }
    
    stop() {
        this.isStopped = true;
        this.timeouts.forEach(t => clearTimeout(t));
        const container = this.app.getVideoContainer(this.zoneId);
        if (container) {
            Array.from(container.children).forEach(child => {
                if (child.tagName === 'VIDEO') {
                    child.pause();
                    child.removeAttribute('src');
                    child.load();
                }
            });
            container.innerHTML = '';
            container.style.display = 'none';
        }
    }

    play(item, onComplete) {
        if (this.isStopped) return;
        if (!this.app.state.uuid || !item.url) {
            console.warn('[VideoPlayer] Item inválido ou sem URL. Avançando playlist.');
            onComplete();
            return;
        }

        const container = this.app.getVideoContainer(this.zoneId);
        container.style.display = 'block';

        const durationMs = (item.duracao || 15) * 1000;
        let isFinished = false;
        let safetyTimeout = null;
        let stallTimeout = null;
        let loadTimeout = null;

        const finish = async (reason) => {
            if (isFinished || this.isStopped) return;
            isFinished = true;

            if (safetyTimeout) clearTimeout(safetyTimeout);
            if (stallTimeout) clearTimeout(stallTimeout);
            if (loadTimeout) clearTimeout(loadTimeout);

            console.log(`[VideoPlayer ${this.zoneId}] Finalizando: "${item.descricao}" (motivo: ${reason})`);
            
            onComplete();
        };

        const finalizeTransition = (newElement) => {
            if (isFinished || this.isStopped) return;
            Array.from(container.children).forEach(child => {
                if (child !== newElement) {
                    if (child.tagName === 'VIDEO') {
                        child.pause();
                        child.removeAttribute('src');
                        child.load();
                    }
                    child.remove();
                }
            });
            container.style.opacity = '1';
        };

        if (item.tipo_midia === 'IMAGEM') {
            const img = document.createElement('img');
            img.id = 'video-bg';
            img.style.cssText = 'position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;';
            img.src = item.url;
            img.onload = () => finalizeTransition(img);
            img.onerror = () => finish('image-error');
            safetyTimeout = setTimeout(() => finish('image-duration'), durationMs);
            this.timeouts.push(safetyTimeout);
            container.appendChild(img);
            
            const transTimeout = setTimeout(() => finalizeTransition(img), 1000);
            this.timeouts.push(transTimeout);

        } else {
            const video = document.createElement('video');
            video.id = 'video-bg';
            video.style.cssText = 'position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;';

            video.setAttribute('muted', 'true');
            video.setAttribute('autoplay', 'true');
            video.setAttribute('playsinline', 'true');
            video.setAttribute('preload', 'auto');
            video.setAttribute('poster', 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7');
            
            video.muted = true;
            video.autoplay = true;

            video.onended = () => finish('video-ended');

            video.onerror = (e) => {
                console.error(`[VideoPlayer ${this.zoneId}] Erro no elemento <video>:`, e, video.error);
                finish('video-error');
            };

            loadTimeout = setTimeout(() => {
                if (!isFinished && video.readyState < 3) {
                    console.warn(`[VideoPlayer ${this.zoneId}] Timeout inicial. URL:`, item.url);
                    finish('load-timeout');
                }
            }, 8000);
            this.timeouts.push(loadTimeout);

            const handlePlaying = () => {
                finalizeTransition(video);
                if (loadTimeout) { clearTimeout(loadTimeout); loadTimeout = null; }
                if (!safetyTimeout) {
                    safetyTimeout = setTimeout(() => finish('safety-duration'), durationMs + 3000);
                    this.timeouts.push(safetyTimeout);
                }
            };
            video.oncanplay = handlePlaying;
            video.onplaying = handlePlaying;

            const handleStall = () => {
                if (isFinished || this.isStopped) return;
                if (stallTimeout) clearTimeout(stallTimeout);
                stallTimeout = setTimeout(() => {
                    if (!isFinished && video.paused) {
                        console.warn(`[VideoPlayer ${this.zoneId}] Buffer travado. Tentando retomar...`);
                        video.play().catch(() => finish('stall-unrecoverable'));
                    }
                }, 5000);
                this.timeouts.push(stallTimeout);
            };

            video.onstalled = handleStall;
            video.onsuspend = () => {
                if (!isFinished && video.readyState < 2) handleStall();
            };

            safetyTimeout = setTimeout(() => finish('emergency-timeout'), durationMs + 15000);
            this.timeouts.push(safetyTimeout);

            container.appendChild(video);

            video.src = item.url;
            video.load();

            const playPromise = video.play();
            if (playPromise !== undefined) {
                playPromise.catch(err => {
                    console.warn(`[VideoPlayer ${this.zoneId}] video.play() rejeitado:`, err.message);
                    if (!isFinished && !this.isStopped) {
                        video.muted = true;
                        video.play().catch(() => finish('autoplay-blocked'));
                    }
                });
            }
        }
    }
}

const API = {
    async pairDevice(code) {
        const response = await fetch(`${CONFIG.API_BASE}/parear/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ codigo: code })
        });

        if (!response.ok) {
            let msg = "Erro desconhecido de integração.";
            try {
                const json = await response.json();
                msg = json.erro || msg;
            } catch (e) { }
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