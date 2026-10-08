/**
 * Network Chat - Frontend UI Script
 * Stage 7: WebSocket Bridge Connection (Browser <--> WebSocket Bridge <--> TCP Server)
 */

document.addEventListener('DOMContentLoaded', () => {
  // Application State
  let currentUser = '';
  let onlineUsers = [];
  let socket = null;

  // WebSocket Bridge address
  const WS_URL = 'ws://127.0.0.1:8765';

  // DOM Elements
  const joinScreen = document.getElementById('join-screen');
  const chatApp = document.getElementById('chat-app');
  const joinForm = document.getElementById('join-form');
  const usernameInput = document.getElementById('username-input');
  const joinBtn = document.getElementById('join-btn');
  const joinError = document.getElementById('join-error');

  const userListElement = document.getElementById('user-list');
  const onlineCountElement = document.getElementById('online-count');
  const messagesContainer = document.getElementById('messages-container');

  const messageForm = document.getElementById('message-form');
  const messageInput = document.getElementById('message-input');

  const statusDot = document.getElementById('connection-status-dot');
  const statusText = document.getElementById('connection-status-text');
  const sidebarStatusVal = document.getElementById('sidebar-status-val');

  // Format current time into readable string (e.g. "10:35 AM")
  function formatCurrentTime() {
    const now = new Date();
    let hours = now.getHours();
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    return `${hours}:${minutes} ${ampm}`;
  }

  // Update UI connection indicator
  function setConnectionStatus(connected, text = 'Connected') {
    if (connected) {
      statusDot.classList.remove('disconnected');
      statusText.textContent = text;
      sidebarStatusVal.classList.remove('disconnected');
      sidebarStatusVal.textContent = text;
    } else {
      statusDot.classList.add('disconnected');
      statusText.textContent = text;
      sidebarStatusVal.classList.add('disconnected');
      sidebarStatusVal.textContent = text;
    }
  }

  // Render the list of online users in the left sidebar
  function renderOnlineUsers() {
    userListElement.innerHTML = '';
    onlineCountElement.textContent = `${onlineUsers.length} online`;

    onlineUsers.forEach((user) => {
      const li = document.createElement('li');
      li.className = 'user-item';

      if (user === currentUser) {
        li.classList.add('is-self');
      }

      const dot = document.createElement('span');
      dot.className = 'user-dot';

      const name = document.createElement('span');
      name.textContent = user === currentUser ? `${user} (You)` : user;

      li.appendChild(dot);
      li.appendChild(name);
      userListElement.appendChild(li);
    });
  }

  // Append a system notification (e.g., "Alice joined the chat")
  function appendSystemMessage(text) {
    const div = document.createElement('div');
    div.className = 'system-notice';
    div.textContent = text;
    messagesContainer.appendChild(div);
    scrollToBottom();
  }

  // Append a chat message row (self or other)
  function appendChatMessage(sender, text, time, isSelf = false) {
    const row = document.createElement('div');
    row.className = `message-row ${isSelf ? 'self' : 'other'}`;

    const meta = document.createElement('div');
    meta.className = 'message-meta';

    if (!isSelf) {
      const senderSpan = document.createElement('span');
      senderSpan.className = 'message-sender';
      senderSpan.textContent = sender;
      meta.appendChild(senderSpan);
    }

    const timeSpan = document.createElement('span');
    timeSpan.className = 'message-time';
    timeSpan.textContent = time;
    meta.appendChild(timeSpan);

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = text;

    row.appendChild(meta);
    row.appendChild(bubble);
    messagesContainer.appendChild(row);

    scrollToBottom();
  }

  // Auto-scroll to latest message
  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Handle incoming messages forwarded from the TCP server through the bridge
  function handleIncomingMessage(raw) {
    const trimmed = raw.trim();
    if (!trimmed) return;

    // 1. Online Users list update sent by the bridge
    if (trimmed.startsWith('[Server] ONLINE_USERS:')) {
      const usersStr = trimmed.replace('[Server] ONLINE_USERS:', '').trim();
      if (usersStr) {
        onlineUsers = usersStr.split(',').map((u) => u.trim()).filter(Boolean);
      } else {
        onlineUsers = [currentUser];
      }
      renderOnlineUsers();
      return;
    }

    // 2. Server welcome message
    if (trimmed.startsWith('[Server] Welcome,')) {
      appendSystemMessage(trimmed);
      return;
    }

    // 3. Server join announcement (e.g. "[Server] Ishita has joined the chat!")
    if (trimmed.startsWith('[Server] ') && trimmed.includes('has joined the chat!')) {
      const match = trimmed.match(/\[Server\] (.+) has joined the chat!/);
      if (match) {
        const joinedUser = match[1].trim();
        appendSystemMessage(`${joinedUser} joined the chat`);
        if (!onlineUsers.includes(joinedUser)) {
          onlineUsers.push(joinedUser);
          renderOnlineUsers();
        }
      } else {
        appendSystemMessage(trimmed);
      }
      return;
    }

    // 4. Server leave announcement (e.g. "[Server] Ishita has left the chat.")
    if (trimmed.startsWith('[Server] ') && trimmed.includes('has left the chat.')) {
      const match = trimmed.match(/\[Server\] (.+) has left the chat\./);
      if (match) {
        const leftUser = match[1].trim();
        appendSystemMessage(`${leftUser} left the chat`);
        onlineUsers = onlineUsers.filter((u) => u !== leftUser);
        renderOnlineUsers();
      } else {
        appendSystemMessage(trimmed);
      }
      return;
    }

    // 5. Generic server system message
    if (trimmed.startsWith('[Server]')) {
      appendSystemMessage(trimmed);
      return;
    }

    // 6. Normal chat message from another client (Format: "Username: message text")
    const colonIndex = trimmed.indexOf(':');
    if (colonIndex !== -1) {
      const sender = trimmed.substring(0, colonIndex).trim();
      const messageText = trimmed.substring(colonIndex + 1).trim();

      // If sender is current user, we already rendered it locally on send
      if (sender !== currentUser) {
        appendChatMessage(sender, messageText, formatCurrentTime(), false);
      }
    } else {
      appendSystemMessage(trimmed);
    }
  }

  // Handle Username Submission (Join Chat)
  joinForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const enteredName = usernameInput.value.trim();
    if (!enteredName) return;

    currentUser = enteredName;

    // Reset error state
    if (joinError) {
      joinError.textContent = '';
      joinError.classList.add('hidden');
    }

    // Update button to Connecting state
    if (joinBtn) {
      joinBtn.disabled = true;
      joinBtn.textContent = 'Connecting...';
    }

    let connectionEstablished = false;

    // Connection timeout fallback
    const connectionTimeout = setTimeout(() => {
      if (!connectionEstablished) {
        showJoinError("Connection timed out. Please ensure both 'server.py' and 'websocket_bridge.py' are running.");
      }
    }, 4000);

    function showJoinError(msg) {
      clearTimeout(connectionTimeout);
      if (joinBtn) {
        joinBtn.disabled = false;
        joinBtn.textContent = 'Join Chat';
      }
      if (joinError) {
        joinError.textContent = msg;
        joinError.classList.remove('hidden');
      }
      if (socket) {
        try { socket.close(); } catch (_) {}
      }
    }

    // Connect to Python WebSocket Bridge
    try {
      socket = new WebSocket(WS_URL);
    } catch (err) {
      showJoinError(`WebSocket error: ${err.message || err}`);
      return;
    }

    socket.onopen = () => {
      connectionEstablished = true;
      clearTimeout(connectionTimeout);

      // Step A: Send username as initial message to the bridge
      socket.send(currentUser);

      // Step B: Switch view to main chat interface
      joinScreen.classList.add('hidden');
      chatApp.classList.remove('hidden');

      setConnectionStatus(true, 'Connected');

      // Initialize online users list with current user
      onlineUsers = [currentUser];
      renderOnlineUsers();

      // Focus message input box
      messageInput.focus();
    };

    socket.onmessage = (event) => {
      handleIncomingMessage(event.data);
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (!connectionEstablished) {
        showJoinError("Could not connect to WebSocket Bridge (ws://127.0.0.1:8765). Please make sure 'python websocket_bridge.py' is running in a terminal.");
      } else {
        setConnectionStatus(false, 'Error');
      }
    };

    socket.onclose = () => {
      if (!connectionEstablished) {
        showJoinError("Connection closed before joining. Please ensure both 'server.py' and 'websocket_bridge.py' are running.");
      } else {
        setConnectionStatus(false, 'Disconnected');
        appendSystemMessage('Disconnected from server.');
      }
    };
  });

  // Handle Sending a Message
  messageForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = messageInput.value.trim();

    if (!text) return;

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      appendSystemMessage('Cannot send: not connected to server.');
      return;
    }

    // Send message to the bridge (which sends it over TCP to server.py)
    socket.send(text);

    // Display user's own message in the chat feed
    appendChatMessage('You', text, formatCurrentTime(), true);

    // If user enters exit command, close connection
    if (text.toLowerCase() === 'exit') {
      appendSystemMessage('You left the chat.');
      socket.close();
    }

    // Clear input field and maintain focus
    messageInput.value = '';
    messageInput.focus();
  });
});
