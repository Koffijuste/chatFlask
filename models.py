# models.py
from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):  # ← Hérite de UserMixin
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    number = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), default="https://via.placeholder.com/40")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'avatar': self.avatar
        }

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    file_url = db.Column(db.String(300), nullable=True)  # ← Ajouté
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_private = db.Column(db.Boolean, default=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def to_dict(self):
        user = User.query.get(self.user_id)
        recipient = User.query.get(self.recipient_id) if self.recipient_id else None
        return {
            'id': self.id,
            'username': self.username,
            'message': self.message,
            'timestamp': self.timestamp.strftime('%H:%M:%S'),
            'user_id': self.user_id,
            'file_url': self.file_url,  # ← Ajouté
            'avatar': user.avatar if user else url_for('static', filename='uploads/avatars/default.png'),
            'is_private': self.is_private,
            'recipient_id': self.recipient_id,
            'recipient_username': recipient.username if recipient else None
        }