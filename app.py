#---------------------------#
# ------ Importações ------ #
#---------------------------#
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import json

#-----------------------------#
# ------ Configurações ------ #
#-----------------------------#
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'M1@2o3u4S536c7r839t10K11312y13!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'painel.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#------------------------#
# ------ Database ------ #
#------------------------#
db = SQLAlchemy(app)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    no_painel = db.Column(db.Boolean, default=True)
    em_oferta = db.Column(db.Boolean, default=False)
    def __repr__(self):
        return f'<Produto {self.nome}>'

class Configuracao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produtos_por_pagina = db.Column(db.Integer, default=10)


#---------------------#
# ------ Rotas ------ #
#---------------------#

# Rota Admin para gerenciar produtos e configurações
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        form_name = request.form.get('form_name')
        
        if form_name == 'add_produto':
            codigo = request.form.get('codigo')
            nome = request.form.get('nome')
            preco_str = request.form.get('preco').replace(',', '.')
            existe = Produto.query.filter_by(codigo=codigo).first()
            
            if existe:
                return jsonify({'success': False, 'message': 'Erro: Já existe um produto com esse código!'}), 400
            try:
                preco = float(preco_str)
                novo_produto = Produto(codigo=codigo, nome=nome, preco=preco)
                db.session.add(novo_produto)
                db.session.commit()

                return jsonify({
                    'success': True, 
                    'message': 'Produto adicionado com sucesso!',
                    'produto': {
                        'id': novo_produto.id,
                        'codigo': novo_produto.codigo,
                        'nome': novo_produto.nome,
                        'preco': f'{novo_produto.preco:.2f}', # Já envia formatado
                        'no_painel': novo_produto.no_painel,
                        'em_oferta': novo_produto.em_oferta
                    }
                }), 201 # 201 = "Created"
                
            except ValueError:
                return jsonify({'success': False, 'message': 'Erro: Preço inválido.'}), 400
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Erro ao salvar: {e}'}), 500

        elif form_name == 'config':
            try:
                # ... (lógica de salvar config) ...
                # Esta parte ainda usa flash/redirect, o que está OK
                # pois não é uma ação frequente.
                config = Configuracao.query.first()
                config.produtos_por_pagina = int(request.form.get('produtos_por_pagina', 10))
                db.session.commit()
                flash('Configurações salvas!', 'success')
            except ValueError:
                flash('Erro: Número de produtos por página inválido.', 'error')
            
            return redirect(url_for('admin')) # Mantém o redirect aqui

    produtos = Produto.query.order_by(Produto.nome).all()
    config = Configuracao.query.first()
    return render_template('admin.html', produtos=produtos, config=config)

# Rota para atualizar produto
@app.route('/admin/update/<int:id>', methods=['POST'])
def update_produto(id):
    produto = Produto.query.get_or_404(id)
    try:
        produto.nome = request.form.get('nome')
        produto.preco = float(request.form.get('preco').replace(',', '.'))
        produto.no_painel = 'no_painel' in request.form 
        produto.em_oferta = 'em_oferta' in request.form
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Produto atualizado!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao atualizar: {e}'}), 500

# Rota para deletar produt
@app.route('/admin/delete/<int:id>', methods=['POST']) 
def delete_produto(id):
    try:
        produto = Produto.query.get_or_404(id)
        db.session.delete(produto)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Produto deletado.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao deletar: {e}'}), 500

# Rota do painel de preços
@app.route('/painel')
def painel():
    config = Configuracao.query.first()
    produtos_ativos = Produto.query.filter_by(no_painel=True).order_by(Produto.nome).all()

    lista_produtos_json = []
    for p in produtos_ativos:
        lista_produtos_json.append({
            'nome': p.nome,
            'preco': p.preco,
            'em_oferta': p.em_oferta
        })

    return render_template('painel.html', 
                           produtos_json=json.dumps(lista_produtos_json), 
                           produtos_por_pagina=config.produtos_por_pagina)

# Rota raiz redireciona para admin
@app.route('/')
def index():
    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Configuracao.query.first():
            config_inicial = Configuracao(produtos_por_pagina=10)
            db.session.add(config_inicial)
            db.session.commit()
            
    app.run(debug=True, host='0.0.0.0', port=5000)