import os
import uuid

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit
from models import db, User, Message
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'temp-survival-key-2025'

# Base de données
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///chat.db'

# Options pour PostgreSQL
if "postgresql" in (database_url or ""):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,
    }

db.init_app(app)

# Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Créer les tables
with app.app_context():
    db.create_all()

# ============= ROUTES =============

@app.route('/')
def home():
    try:
        if current_user.is_authenticated:
            return redirect(url_for('home'))  # Temporaire — on n’a pas index.html
    except:
        pass
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('✅ Connecté !', 'success')
            return redirect(url_for('home'))
        else:
            flash('❌ Mauvais login.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('❌ Déjà pris.', 'danger')
            return render_template('register.html')
        user = User(username=username)
        user.password_hash = generate_password_hash(password)
        db.session.add(user)
        db.session.commit()
        flash('✅ Créé ! Connectez-vous.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    from flask_login import logout_user
    logout_user()
    flash('👋 Déconnecté.', 'info')
    return redirect(url_for('home'))

# Gestionnaires d'erreurs
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# ============= LANCEMENT =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)  # ← PAS DE SOCKET.IO POUR L'INSTANT