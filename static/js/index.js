const socket = io();
        const userId = {{ current_user.id }};
        const isAdmin = userId === 1;

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

            msgDiv.innerHTML = `
                <div class="message-content">
                    <img src="${data.avatar || 'https://via.placeholder.com/40'}" 
                         alt="Avatar" class="message-avatar">
                    <div class="message-body">
                        <div class="message-header">
                            <span class="message-username">${data.username}</span>
                            <span class="message-timestamp">${data.timestamp}</span>
                        </div>
                        <div class="message-text">${data.message}</div>
                    </div>
                </div>
            `;

            messagesDiv.appendChild(msgDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        });

        socket.on('user_count', function(count) {
            document.getElementById('count').innerText = count;
            document.getElementById('user-count').innerText = count;
        });

        // Envoyer avec Entrée
        document.getElementById('message').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });