    const socket = io({ transports: ['polling'] });
    const userId = {{ current_user.id }};
    const isAdmin = userId === 1;

    // Son de notification
    const notificationSound = new Audio("https://cdn.pixabay.com/download/audio/2022/03/16/audio_7f9260d520.mp3?filename=notification-sound-73555.mp3");

    // Fonction pour jouer le son + vibration (mobile)
    function notify() {
        notificationSound.play().catch(e => console.log("Son bloqué par le navigateur"));
        if ("vibrate" in navigator) {
            navigator.vibrate([200, 100, 200]);
        }
    }

    // Répondre à un message
    let replyingTo = null;

    function setReply(messageId, username, text) {
        replyingTo = { id: messageId, username, text };
        const replyBar = document.getElementById('reply-bar');
        replyBar.innerHTML = `
            <div style="background:#e3f2fd; padding:8px; border-radius:6px; font-size:0.9rem; margin-bottom:10px;">
                ↳ En réponse à <strong>${username}</strong> : "${text.substring(0, 50)}${text.length > 50 ? '...' : ''}"
                <button onclick="cancelReply()" style="float:right; background:none; border:none; color:#f72585; cursor:pointer;">✕</button>
            </div>
        `;
        replyBar.style.display = 'block';
    }

    function cancelReply() {
        replyingTo = null;
        const replyBar = document.getElementById('reply-bar');
        replyBar.style.display = 'none';
        replyBar.innerHTML = '';
    }

    // Supprimer un message
    function deleteMessage(messageId) {
        if (confirm("Voulez-vous vraiment supprimer ce message ?")) {
            socket.emit('delete_message', { message_id: messageId });
        }
    }

    // Envoyer un message
    socket.on('update_online_users', function(users) {
    const userList = document.getElementById('online-users');
    if (!userList) return;

    userList.innerHTML = '';
    users.forEach(user => {
        if (user.id !== userId) { // Ne pas s'afficher soi-même
            const li = document.createElement('li');
            li.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px; padding: 6px 0; cursor: pointer;" onclick="startPrivateChat(${user.id}, '${user.username}')">
                    <img src="${user.avatar}" style="width: 30px; height: 30px; border-radius: 50%;">
                    <span>${user.username}</span>
                    <span style="color: #007bff; font-size: 0.9rem;">✉️ MP</span>
                </div>
            `;
            userList.appendChild(li);
        }
    });
});

function startPrivateChat(recipientId, recipientName) {
    // Ouvre une "conversation privée" — on va juste changer l'UI pour l'instant
    alert(`Tu vas envoyer un message privé à ${recipientName} (ID: ${recipientId})`);

    // Tu peux ajouter un système de "salon privé" ou taguer le message comme privé
    // Pour l'instant, on va juste ajouter un flag dans le message
    // On va modifier sendMessage() pour gérer ça
}

    socket.on('receive_message', function(data) {
    notify();

    const messagesDiv = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message';
    msgDiv.setAttribute('data-message-id', data.id);

    let prefix = '';
    if (data.is_private) {
        const fromMe = data.user_id === userId;
        const target = fromMe ? `→ ${data.recipient_username}` : `← ${data.username}`;
        prefix = `<span style="background: #ffe0b2; color: #e65100; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem;">✉️ MP ${target}</span><br>`;
    }

    const escapedMessage = data.message
        .replace(/&/g, "&amp;")
        .replace(/</g, "<")
        .replace(/>/g, ">")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    msgDiv.innerHTML = `
        <div class="meta">
            <div>
                <img src="${data.avatar || 'https://via.placeholder.com/40'}" class="avatar" alt="avatar">
                <span class="username">${data.username}</span>
            </div>
            <span class="time">${data.timestamp}</span>
        </div>
        ${prefix}
        <div class="text" onclick="setReply(${data.id}, '${data.username.replace(/'/g, "\\'")}', '${data.message.replace(/'/g, "\\'")}')">
            ${escapedMessage}
        </div>
        ${userId === data.user_id || isAdmin ? 
            `<button class="delete-btn" onclick="deleteMessage(${data.id})">🗑️</button>` 
            : ''}
    `;

    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
});

    // Suppression côté client
    socket.on('message_deleted', function(data) {
        const msgDiv = document.querySelector(`.message[data-message-id="${data.message_id}"]`);
        if (msgDiv) msgDiv.remove();
    });

    // Mise à jour du compteur d'utilisateurs
    socket.on('user_count', function(count) {
        document.getElementById('count').innerText = count;
    });

    // Recherche en temps réel
    document.getElementById('search-input')?.addEventListener('input', function(e) {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.message').forEach(msg => {
            const text = msg.querySelector('.text')?.innerText.toLowerCase() || '';
            const username = msg.querySelector('.username')?.innerText.toLowerCase() || '';
            msg.style.display = (text.includes(term) || username.includes(term)) ? 'block' : 'none';
        });
    });

    // Envoyer avec Entrée
    document.getElementById('message').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });

    socket.on('update_online_users', function(users) {
    const userList = document.getElementById('online-users');
    if (!userList) return;

    userList.innerHTML = '';
    users.forEach(user => {
        if (user.id !== userId) { // Ne pas s'afficher soi-même
            const li = document.createElement('li');
            li.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px; padding: 6px 0; cursor: pointer;" onclick="startPrivateChat(${user.id}, '${user.username}')">
                    <img src="${user.avatar}" style="width: 30px; height: 30px; border-radius: 50%;">
                    <span>${user.username}</span>
                    <span style="color: #007bff; font-size: 0.9rem;">✉️ MP</span>
                </div>
            `;
            userList.appendChild(li);
        }
    });
});

function startPrivateChat(recipientId, recipientName) {
    // Ouvre une "conversation privée" — on va juste changer l'UI pour l'instant
    alert(`Tu vas envoyer un message privé à ${recipientName} (ID: ${recipientId})`);

    // Tu peux ajouter un système de "salon privé" ou taguer le message comme privé
    // Pour l'instant, on va juste ajouter un flag dans le message
    // On va modifier sendMessage() pour gérer ça
}


    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        document.getElementById('theme-toggle').innerText = '☀️';
    }

    // Toggle thème
    document.getElementById('theme-toggle')?.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        this.innerText = isDark ? '☀️' : '🌙';
    });