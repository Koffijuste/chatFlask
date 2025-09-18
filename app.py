# app.py — VERSION ULTIMEMENT CORRIGÉE POUR RENDER
import os
import uuid

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit
from models import db, User, Message
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect, validate_csrf
from wtforms import ValidationError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-chat-key-2025!'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/avatars'

# Créer le dossier uploads si nécessaire
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Récupérer DATABASE_URL depuis l'environnement
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///chat.db'

# 👇 CONFIGURATION CRUCIALE : PAS d'options SQLite pour PostgreSQL
if "postgresql" in (database_url or ""):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 3600,
    }
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "connect_args": {
            "check_same_thread": False
        }
    }

# ✅ Initialiser la protection CSRF
csrf = CSRFProtect(app)

# Initialiser les extensions
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", engineio_logger=False, logger=False)

# 🔑 Initialiser Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Liste des utilisateurs connectés
connected_users = {}

# 👇 CRÉER LES TABLES AVANT TOUTE REQUÊTE
with app.app_context():
    db.create_all()

# ============= ROUTES =============

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('✅ Connexion réussie !', 'success')
            return redirect(url_for('index'))
        else:
            flash('❌ Nom d’utilisateur ou mot de passe incorrect.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('❌ Les mots de passe ne correspondent pas.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('❌ Ce nom d’utilisateur est déjà pris.', 'danger')
            return render_template('register.html')

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('✅ Compte créé avec succès ! Connectez-vous.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/')
def home():
    try:
        if current_user.is_authenticated:
            return redirect(url_for('index'))
    except:
        pass  # Ignore toute erreur liée à current_user
    return render_template('home.html')


@app.route('/logout')
@login_required
def logout():
    user_id = current_user.id
    if user_id in connected_users:
        del connected_users[user_id]
        socketio.emit('user_count', len(connected_users))

    logout_user()
    flash('👋 Vous êtes déconnecté.', 'info')
    return redirect(url_for('login'))

# ... (le reste de tes routes admin, profile, stats, etc. reste inchangé) ...

# ============= SOCKET.IO =============

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        connected_users[current_user.id] = {
            'sid': request.sid,
            'username': current_user.username,
            'avatar': current_user.avatar
        }
        emit('user_count', len(connected_users))
        emit('update_online_users', get_online_users())

def get_online_users():
    return [
        {
            'id': uid,
            'username': user['username'],
            'avatar': user['avatar']
        }
        for uid, user in connected_users.items()
    ]

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated and current_user.id in connected_users:
        del connected_users[current_user.id]
        emit('user_count', len(connected_users))
        emit('update_online_users', get_online_users())

@socketio.on('send_message')
def handle_message(data):
    if not current_user.is_authenticated:
        return

    message_text = data.get('message', '').strip()
    if not message_text:
        return

    is_private = data.get('is_private', False)
    recipient_id = data.get('recipient_id')

    new_message = Message(
        username=current_user.username,
        message=message_text,
        user_id=current_user.id,
        is_private=is_private,
        recipient_id=recipient_id if is_private else None
    )
    db.session.add(new_message)
    db.session.commit()

    message_data = new_message.to_dict()

    if is_private and recipient_id:
        recipient = connected_users.get(recipient_id)
        if recipient:
            emit('receive_message', message_data, room=recipient['sid'])
        emit('receive_message', message_data, room=request.sid)
    else:
        emit('receive_message', message_data, broadcast=True)

@socketio.on('delete_message')
def handle_delete_message(data):
    if not current_user.is_authenticated:
        return

    message_id = data.get('message_id')
    message = Message.query.get(message_id)

    if message and (message.user_id == current_user.id or current_user.id == 1):
        db.session.delete(message)
        db.session.commit()
        emit('message_deleted', {'message_id': message_id}, broadcast=True)

# Gestionnaires d'erreurs personnalisés
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# ============= LANCEMENT =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # ← Render utilise 10000 par défaut
    socketio.run(app, host='0.0.0.0', port=port, debug=False)