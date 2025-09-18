# app.py — VERSION ULTIME POUR RENDER + EVENTLET + POSTGRESQL
import os
import eventlet
eventlet.monkey_patch()  # ← DOIT ÊTRE AU TOUT DÉBUT

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit
from models import db, User, Message
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-chat-key-2025!'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/avatars'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Récupérer DATABASE_URL
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///chat.db'

# 👇 CONFIGURATION POSTGRESQL POUR EVENTLET
if "postgresql" in (database_url or ""):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,
        "pool_timeout": 30,
        "connect_args": {
            "sslmode": "require",  # ← Important pour Render
        }
    }
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "connect_args": {
            "check_same_thread": False
        }
    }

# Initialiser les extensions
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

connected_users = {}

with app.app_context():
    db.create_all()

# ============= ROUTES =============

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return render_template('home.html')

@app.route('/students/chat')
@login_required
def chat():
    try:
        messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()
        messages.reverse()
        return render_template('index.html', messages=messages, user=current_user)
    except Exception as e:
        flash('❌ Erreur lors du chargement des messages.', 'danger')
        print(f"Erreur chat : {e}")
        return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        try:
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                flash('✅ Connexion réussie !', 'success')
                return redirect(url_for('index'))
            else:
                flash('❌ Mauvais login.', 'danger')
        except Exception as e:
            flash('❌ Erreur serveur. Réessayez.', 'danger')
            print(f"Erreur login : {e}")
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

        try:
            if User.query.filter_by(username=username).first():
                flash('❌ Ce nom d’utilisateur est déjà pris.', 'danger')
                return render_template('register.html')

            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash('✅ Compte créé ! Connectez-vous.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('❌ Erreur serveur. Réessayez.', 'danger')
            print(f"Erreur register : {e}")

    return render_template('register.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    user_id = current_user.id
    if user_id in connected_users:
        del connected_users[user_id]
        socketio.emit('user_count', len(connected_users))
    logout_user()
    flash('👋 Déconnecté.', 'info')
    return redirect(url_for('login'))

# Gestionnaires d'erreurs
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

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

@socketio.on('send_message')
def handle_message(data):
    if not current_user.is_authenticated:
        return

    message_text = data.get('message', '').strip()
    if not message_text:
        return

    new_message = Message(
        username=current_user.username,
        message=message_text,
        user_id=current_user.id,
        is_private=False
    )
    db.session.add(new_message)
    db.session.commit()

    message_data = {
        'id': new_message.id,
        'username': new_message.username,
        'message': new_message.message,
        'timestamp': new_message.timestamp.strftime('%H:%M:%S'),
        'user_id': new_message.user_id
    }

    emit('receive_message', message_data, broadcast=True)


@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated and current_user.id in connected_users:
        del connected_users[current_user.id]
        emit('user_count', len(connected_users))
        emit('update_online_users', get_online_users())

# ============= LANCEMENT =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)