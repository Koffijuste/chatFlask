# app.py — VERSION MINIMALE POUR TESTER LE DÉMARRAGE
import os
from flask import Flask, render_template

app = Flask(__name__)
app.config['SECRET_KEY'] = 'temp-key-for-test'

# Route de base
@app.route('/')
def home():
    return "<h1>✅ App démarrée !</h1><p>Si tu vois ça, Flask tourne.</p>"

# Gestionnaire d'erreur 500
@app.errorhandler(500)
def internal_error(e):
    return "<h1>❌ Erreur 500</h1><p>Problème interne.</p>", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)