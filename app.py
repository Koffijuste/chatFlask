# app.py — VERSION CORRIGÉE POUR RENDER + POSTGRESQL
import os
import uuid
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit
from models import db, User, Message
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect, validate_csrf
from wtforms import ValidationError

# 👇 Force SQLite en mode thread-safe AVANT SQLAlchemy
sqlite3.threadsafety = 3

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

# 👇 Configurer les options du moteur SQL en fonction du type de base
if database_url and database_url.startswith("postgresql://"):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        # PAS de "check_same_thread" pour PostgreSQL → CRASH sinon
    }
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "connect_args": {
            "check_same_thread": False  # Seulement pour SQLite
        }
    }

# ✅ Initialiser la protection CSRF
csrf = CSRFProtect(app)

# Initialiser les extensions
db.init_app(app)
socketio = SocketIO(app)

# 🔑 Initialiser Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Liste des utilisateurs connectés
connected_users = {}

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

@app.route('/admin')
@login_required
def admin():
    if current_user.id != 1:
        flash('🚫 Accès refusé. Réservé à l’administrateur.', 'danger')
        return redirect(url_for('index'))

    users = User.query.order_by(User.id).all()
    messages = Message.query.order_by(Message.timestamp.desc()).limit(100).all()

    total_users = User.query.count()
    total_messages = Message.query.count()
    total_private_messages = Message.query.filter_by(is_private=True).count()

    return render_template(
        'admin.html',
        users=users,
        messages=messages,
        total_users=total_users,
        total_messages=total_messages,
        total_private_messages=total_private_messages
    )

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.id != 1:
        return jsonify({'success': False, 'error': 'Accès refusé'}), 403

    if user_id == 1:
        return jsonify({'success': False, 'error': 'Impossible de supprimer l’admin'}), 400

    try:
        token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
        if not token:
            raise ValidationError('Token CSRF manquant')
        validate_csrf(token)
    except ValidationError:
        return jsonify({'success': False, 'error': 'Token CSRF invalide'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'Utilisateur non trouvé'}), 404

    Message.query.filter(
        (Message.user_id == user_id) | (Message.recipient_id == user_id)
    ).delete()

    db.session.delete(user)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/admin/delete_message/<int:message_id>', methods=['POST'])
@login_required
def admin_delete_message(message_id):
    if current_user.id != 1:
        return jsonify({'success': False, 'error': 'Accès refusé'}), 403

    try:
        token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
        if not token:
            raise ValidationError('Token CSRF manquant')
        validate_csrf(token)
    except ValidationError:
        return jsonify({'success': False, 'error': 'Token CSRF invalide'}), 400

    message = Message.query.get(message_id)
    if not message:
        return jsonify({'success': False, 'error': 'Message non trouvé'}), 404

    db.session.delete(message)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/')
@login_required
def index():
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()
    messages.reverse()
    return render_template('index.html', messages=messages)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'avatar' not in request.files:
            flash('❌ Aucun fichier sélectionné', 'danger')
            return redirect(request.url)

        file = request.files['avatar']
        if file.filename == '':
            flash('❌ Aucun fichier sélectionné', 'danger')
            return redirect(request.url)

        if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}:
            filename = secure_filename(f"{current_user.id}_{uuid.uuid4().hex[:8]}.{file.filename.rsplit('.', 1)[1].lower()}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            current_user.avatar = f"/static/uploads/avatars/{filename}"
            db.session.commit()
            flash('✅ Avatar mis à jour !', 'success')
            return redirect(url_for('profile'))

    return render_template('profile.html', user=current_user)

@login_manager.unauthorized_handler
def unauthorized():
    flash('🔒 Veuillez vous connecter pour accéder à cette page.', 'warning')
    return redirect(url_for('login'))

@app.route('/stats')
@login_required
def stats():
    from sqlalchemy import func

    week_stats = db.session.query(
        func.strftime('%Y-%m-%d', Message.timestamp).label('day'),
        func.count(Message.id).label('count')
    ).group_by('day').order_by('day').limit(7).all()

    top_user = db.session.query(
        User.username,
        func.count(Message.id).label('msg_count')
    ).join(
        Message, Message.user_id == User.id
    ).group_by(
        User.id
    ).order_by(
        func.count(Message.id).desc()
    ).first()

    total_messages = Message.query.count()
    total_users = User.query.count()

    return render_template('stats.html',
        week_stats=week_stats,
        top_user=top_user,
        total_messages=total_messages,
        total_users=total_users)

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
    is_private = data.get('is_private', False)
    recipient_id = data.get('recipient_id')

    if not message_text:
        return

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

# ============= LANCEMENT =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)