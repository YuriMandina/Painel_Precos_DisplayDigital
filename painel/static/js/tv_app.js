/**
 * TV App - Display Digital
 * Responsável por gerenciar a reprodução de conteúdo (Playlist, Vídeos/Imagens e Tabelas de Preço).
 */

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

class TVApp {
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
        this._updateOrientation(newData.config.orientacao);

        const newHash = JSON.stringify(newData.playlist_final);
        
        if (newHash !== this.state.playlistHash) {
            console.log("Nova ordem/playlist detectada. Atualizando a tela...");
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

// --- GERENCIADOR DE PLAYLIST ---
class PlaylistManager {
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
                "<h2 style='color:#666; text-align:center; margin-top:20vh;'>Aguardando configuração...</h2>";
            
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

// --- RENDERIZADOR DE GRADE (TABELA) ---
class GridRenderer {
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

        let productsToShow = allProducts;
        if (itemPlaylist.familia_id) {
            productsToShow = allProducts.filter(p => p.familia === itemPlaylist.familia_id);
        }

        // --- BLINDAGEM MÁXIMA DA TV ---
        if (itemPlaylist.hidden_products && Array.isArray(itemPlaylist.hidden_products)) {
            // Converte todos os IDs recebidos do servidor para Texto
            const hiddenIds = itemPlaylist.hidden_products.map(String);
            
            productsToShow = productsToShow.filter(p => {
                // Garante que o ID do produto exista e seja texto
                const productId = String(p.id);
                // Se a ID estiver na lista negra, retorna falso e arranca ele da tabela
                return !hiddenIds.includes(productId);
            });
        }

        if (productsToShow.length === 0) {
            container.innerHTML = "<h2 style='text-align:center; color:#666; width:100%; margin-top:20vh;'>Nenhum produto a exibir nesta tabela.</h2>";
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

// --- REPRODUTOR DE VÍDEO E IMAGENS ---
class VideoPlayer {
    constructor(app) {
        this.app = app;
    }

    play(item, onComplete) {
        if (!this.app.state.uuid) {
            onComplete();
            return;
        }

        const container = this.app.getVideoContainer();
        container.innerHTML = '';
        container.style.display = 'block';

        const mediaUrl = item.url;
        if (!mediaUrl) {
            onComplete();
            return;
        }

        const durationMs = (item.duracao || 15) * 1000;
        let safetyTimeout;
        let isFinished = false; 

        const finish = () => {
            if (isFinished) return;
            isFinished = true;
            if (safetyTimeout) clearTimeout(safetyTimeout);
            onComplete();
        };

        if (item.tipo_midia === 'IMAGEM') {
            const img = document.createElement('img');
            img.id = 'video-bg'; 
            img.src = mediaUrl;
            img.onload = () => {
                safetyTimeout = setTimeout(finish, durationMs);
            };
            img.onerror = finish;
            container.appendChild(img);
        } else {
            const video = document.createElement('video');
            video.id = 'video-bg';
            video.src = mediaUrl;
            video.muted = true;
            video.autoplay = true;
            video.playsInline = true;

            safetyTimeout = setTimeout(finish, durationMs + 2000);

            video.onerror = finish;
            video.onended = finish;

            container.appendChild(video);
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
            const error = new Error(`Erro API: ${response.status}`);
            error.status = response.status;
            throw error;
        }
        return await response.json();
    }
};