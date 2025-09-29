document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const userId = {{ current_user.number if current_user.is_authenticated else 'null' }};
    const isAdmin = userId === 0507707886;

    // Toggle sidebar
    document.getElementById('menu-toggle').addEventListener('click', function() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('main-content');
        sidebar.classList.toggle('active');
        mainContent.classList.toggle('sidebar-open');
    });

    // Close sidebar when clicking outside (mobile)
    document.addEventListener('click', function(e) {
        const sidebar = document.getElementById('sidebar');
        const toggle = document.getElementById('menu-toggle');
        if (window.innerWidth <= 768 && sidebar.classList.contains('active')) {
            if (!sidebar.contains(e.target) && e.target !== toggle) {
                sidebar.classList.remove('active');
                document.getElementById('main-content').classList.remove('sidebar-open');
            }
        }
    });

    function sendMessage() {
        const messageInput = document.getElementById('message');
        const message = messageInput.value.trim();
        if (!message) return;

        socket.emit('send_message', { message: message });
        messageInput.value = '';
    }

    socket.on('receive_message', function(data) {
        const messagesDiv = document.getElementById('chat-messages');
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message';
        msgDiv.setAttribute('data-message-id', data.id);

        let content = `<strong>${data.username} :</strong> `;
        if (data.file_url) {
            const ext = data.file_url.split('.').pop().toLowerCase();
            if (['png', 'jpg', 'jpeg', 'gif'].includes(ext)) {
                content += `<br><img src="${data.file_url}" style="max-width:300px; border-radius:8px; margin-top:8px;">`;
            } else {
                content += `<br><a href="${data.file_url}" target="_blank">📎 ${data.file_url.split('/').pop()}</a>`;
            }
        }
        if (data.message) {
            content += `<br>${data.message}`;
        }
        content += `<br><small>${data.timestamp}</small>`;

        msgDiv.innerHTML = content;
        messagesDiv.appendChild(msgDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    });

    socket.on('user_count', function(count) {
        document.getElementById('count').innerText = count;
        document.getElementById('user-count').innerText = count;
    });

    socket.on('connect', function() {
        console.log('Connecté au serveur Socket.IO');
    });

    // Envoyer avec Entrée
    document.getElementById('message').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });

});