# Painel de Preços Digital

Este é um projeto de sistema de Painel de Preços Digital, ideal para exibir preços de produtos (como em um açougue, padaria ou mercado) em uma TV ou monitor.

O sistema é composto por duas partes principais:
1.  **Painel de Exibição (`/painel`)**: Uma tela pública, otimizada para TVs (16:9), que exibe os produtos em um carrossel automático.
2.  **Painel Administrativo (`/admin`)**: Uma área privada, protegida e responsiva (feita com Bootstrap 5), para gerenciar os produtos e as configurações do painel.

## Funcionalidades

### Painel de Exibição (TV)
* **Exibição Otimizada:** Design em proporção 16:9, preenchendo a tela da TV.
* **Carrossel Automático:** Os produtos são divididos em páginas que rotacionam automaticamente a cada 8 segundos.
* **Destaque de Ofertas:** Produtos marcados como "Em Oferta" recebem um destaque visual (cor e tag).
* **Layout Limpo:** Foco na legibilidade, com layout em duas colunas.
* **Transição Suave:** Efeito de "slide e fade" ao trocar de página.

### Painel Administrativo
* **Interface Responsiva:** Construído com Bootstrap 5, funciona bem em desktops ou celulares.
* **CRUD de Produtos:**
    * **Create:** Adicionar novos produtos (código, nome, preço).
    * **Read:** Listar todos os produtos cadastrados.
    * **Update:** Atualizar nome, preço, e os status "No Painel" e "Em Oferta" diretamente na tabela.
    * **Delete:** Remover produtos.
* **Configurações Gerais:**
    * Definir o número de produtos exibidos por página no carrossel da TV (limite de 18).

## Tecnologias Utilizadas

* **Backend:**
    * Python 3
    * Flask (Micro-framework web)
    * Flask-SQLAlchemy (ORM para o banco de dados)
    * SQLite (Banco de dados leve, baseado em arquivo)
* **Frontend (Admin):**
    * HTML5
    * Jinja2 (Template Engine)
    * Bootstrap 5 (CSS Framework)
    * Bootstrap Icons
* **Frontend (Painel):**
    * HTML5
    * Jinja2
    * CSS3 (Grid Layout, Flexbox, Animações)
    * JavaScript (ES6+)

## Como Executar o Projeto

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/YuriMandina/Painel_Precos_DisplayDigital.git
    cd Painel_Precos_DisplayDigital
    ```

2.  **Crie e ative um ambiente virtual (Recomendado):**
    ```bash
    # Criar o ambiente
    python -m venv venv
    
    # Ativar no Windows
    .\venv\Scripts\activate
    
    # Ativar no macOS/Linux
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Execute a aplicação:**
    ```bash
    python app.py
    ```
    O servidor iniciará em modo de debug.

5.  **Acesse as rotas no seu navegador:**
    * **Painel Admin:** `http://127.0.0.1:5000/admin`
    * **Painel de Exibição:** `http://127.0.0.1:5000/painel`
