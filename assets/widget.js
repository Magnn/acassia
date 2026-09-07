/**
 * Acássia Webchat Widget — v1.0
 * Embeddable omni-channel widget (ManyChat / ChatbotX style).
 * 
 * Usage:
 * <script src="https://acassia-production.up.railway.app/assets/widget.js" 
 *         data-tenant="default" 
 *         data-title="Atendimento" 
 *         data-color="#9333ea"></script>
 */
(function () {
  if (window.__ACASSIA_WEBCHAT_LOADED__) return;
  window.__ACASSIA_WEBCHAT_LOADED__ = true;

  // 1. Obter script e atributos de configuração
  const currentScript = document.currentScript || (function () {
    const scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  const tenantId = (currentScript && currentScript.getAttribute('data-tenant')) || 'default';
  const chatTitle = (currentScript && currentScript.getAttribute('data-title')) || 'Atendimento';
  const primaryColor = (currentScript && currentScript.getAttribute('data-color')) || '#9333ea';
  const apiBase = (currentScript && currentScript.getAttribute('data-api')) || (function () {
    try {
      const url = new URL(currentScript.src);
      return url.origin;
    } catch {
      return window.location.origin;
    }
  })();

  // 2. Estado local
  let isOpen = false;
  let sessionId = localStorage.getItem('acassia_webchat_session_' + tenantId) || '';
  let lastMessageId = 0;
  let pollInterval = null;

  // 3. Injetar estilos
  const style = document.createElement('style');
  style.innerHTML = `
    #acassia-widget-container {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    #acassia-bubble-btn {
      width: 60px;
      height: 60px;
      border-radius: 30px;
      background: ${primaryColor};
      box-shadow: 0 8px 24px rgba(0,0,0,0.25);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      border: none;
      outline: none;
    }
    #acassia-bubble-btn:hover {
      transform: scale(1.08);
      box-shadow: 0 12px 28px rgba(0,0,0,0.35);
    }
    #acassia-chat-box {
      position: absolute;
      bottom: 74px;
      right: 0;
      width: 380px;
      height: 560px;
      max-width: calc(100vw - 32px);
      max-height: calc(100vh - 100px);
      background: #0f1117;
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 20px;
      box-shadow: 0 12px 48px rgba(0,0,0,0.5);
      display: none;
      flex-direction: column;
      overflow: hidden;
      transition: opacity 0.2s ease, transform 0.2s ease;
      transform-origin: bottom right;
    }
    #acassia-chat-box.open {
      display: flex;
      animation: acassia-pop 0.25s ease-out;
    }
    @keyframes acassia-pop {
      from { opacity: 0; transform: scale(0.9) translateY(20px); }
      to { opacity: 1; transform: scale(1) translateY(0); }
    }
    .acassia-header {
      padding: 16px 20px;
      background: rgba(255,255,255,0.03);
      border-bottom: 1px solid rgba(255,255,255,0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .acassia-header-info {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .acassia-avatar {
      width: 36px;
      height: 36px;
      border-radius: 12px;
      background: ${primaryColor};
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      color: white;
      font-size: 16px;
    }
    .acassia-title {
      font-size: 15px;
      font-weight: 700;
      color: #fff;
      margin: 0;
    }
    .acassia-status {
      font-size: 11px;
      color: #22c55e;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .acassia-status::before {
      content: '';
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #22c55e;
    }
    .acassia-close-btn {
      background: transparent;
      border: none;
      color: #888;
      cursor: pointer;
      font-size: 18px;
      padding: 4px;
    }
    .acassia-close-btn:hover { color: #fff; }
    .acassia-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .acassia-msg {
      max-width: 82%;
      padding: 10px 14px;
      font-size: 13px;
      line-height: 1.45;
      border-radius: 14px;
      word-break: break-word;
    }
    .acassia-msg.assistant {
      align-self: flex-start;
      background: #1a1d26;
      color: #e2e8f0;
      border-bottom-left-radius: 4px;
      border: 1px solid rgba(255,255,255,0.06);
    }
    .acassia-msg.user {
      align-self: flex-end;
      background: ${primaryColor};
      color: #fff;
      border-bottom-right-radius: 4px;
    }
    .acassia-input-area {
      padding: 12px 16px;
      border-top: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.02);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .acassia-input {
      flex: 1;
      background: #161821;
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 12px;
      padding: 10px 14px;
      color: #fff;
      font-size: 13px;
      outline: none;
    }
    .acassia-input:focus {
      border-color: ${primaryColor};
    }
    .acassia-send-btn {
      width: 40px;
      height: 40px;
      border-radius: 12px;
      background: ${primaryColor};
      border: none;
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: opacity 0.2s;
    }
    .acassia-send-btn:disabled { opacity: 0.5; cursor: default; }
    .acassia-typing {
      display: flex;
      gap: 4px;
      padding: 10px 14px;
      background: #1a1d26;
      border-radius: 14px;
      width: fit-content;
      align-self: flex-start;
    }
    .acassia-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #888;
      animation: acassia-blink 1.2s infinite ease-in-out;
    }
    .acassia-dot:nth-child(2) { animation-delay: 0.2s; }
    .acassia-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes acassia-blink {
      0%, 100% { opacity: 0.3; transform: scale(0.8); }
      50% { opacity: 1; transform: scale(1.1); }
    }
  `;
  document.head.appendChild(style);

  // 4. Criar elementos DOM
  const container = document.createElement('div');
  container.id = 'acassia-widget-container';

  container.innerHTML = `
    <button id="acassia-bubble-btn" aria-label="Abrir chat">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
    </button>
    <div id="acassia-chat-box">
      <div class="acassia-header">
        <div class="acassia-header-info">
          <div class="acassia-avatar">A</div>
          <div>
            <h4 class="acassia-title">${chatTitle}</h4>
            <span class="acassia-status">Online agora</span>
          </div>
        </div>
        <button class="acassia-close-btn" id="acassia-close-btn">&times;</button>
      </div>
      <div class="acassia-messages" id="acassia-messages"></div>
      <div class="acassia-input-area">
        <input type="text" class="acassia-input" id="acassia-input" placeholder="Digite sua mensagem..." autocomplete="off" />
        <button class="acassia-send-btn" id="acassia-send-btn" aria-label="Enviar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(container);

  // 5. Referências e eventos
  const bubbleBtn = document.getElementById('acassia-bubble-btn');
  const chatBox = document.getElementById('acassia-chat-box');
  const closeBtn = document.getElementById('acassia-close-btn');
  const messagesList = document.getElementById('acassia-messages');
  const inputEl = document.getElementById('acassia-input');
  const sendBtn = document.getElementById('acassia-send-btn');

  function toggleChat() {
    isOpen = !isOpen;
    if (isOpen) {
      chatBox.classList.add('open');
      inputEl.focus();
      initChat();
      startPolling();
    } else {
      chatBox.classList.remove('open');
      stopPolling();
    }
  }

  bubbleBtn.addEventListener('click', toggleChat);
  closeBtn.addEventListener('click', toggleChat);

  function appendMessage(text, sender) {
    const msg = document.createElement('div');
    msg.className = `acassia-msg ${sender}`;
    msg.innerText = text;
    messagesList.appendChild(msg);
    messagesList.scrollTop = messagesList.scrollHeight;
  }

  function showTyping() {
    const typing = document.createElement('div');
    typing.id = 'acassia-typing-indicator';
    typing.className = 'acassia-typing';
    typing.innerHTML = '<span class="acassia-dot"></span><span class="acassia-dot"></span><span class="acassia-dot"></span>';
    messagesList.appendChild(typing);
    messagesList.scrollTop = messagesList.scrollHeight;
  }

  function hideTyping() {
    const typing = document.getElementById('acassia-typing-indicator');
    if (typing) typing.remove();
  }

  // 6. Comunicação com a API
  async function initChat() {
    try {
      const res = await fetch(`${apiBase}/api/public/webchat/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, session_id: sessionId }),
      });
      const data = await res.json();
      if (data.ok) {
        sessionId = data.session_id;
        localStorage.setItem('acassia_webchat_session_' + tenantId, sessionId);

        messagesList.innerHTML = '';
        if (data.messages && data.messages.length > 0) {
          data.messages.forEach(m => {
            appendMessage(m.text, m.sender);
            if (m.id > lastMessageId) lastMessageId = m.id;
          });
        } else {
          appendMessage('Olá! Como posso ajudar você hoje?', 'assistant');
        }
      }
    } catch (err) {
      console.warn('[Acassia Webchat] Falha na inicialização:', err);
    }
  }

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;

    inputEl.value = '';
    appendMessage(text, 'user');
    showTyping();
    sendBtn.disabled = true;

    try {
      const res = await fetch(`${apiBase}/api/public/webchat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: tenantId,
          session_id: sessionId,
          text: text,
        }),
      });
      const data = await res.json();
      hideTyping();
      sendBtn.disabled = false;

      if (data.ok && data.replies && data.replies.length > 0) {
        data.replies.forEach(r => appendMessage(r, 'assistant'));
      }
    } catch (err) {
      hideTyping();
      sendBtn.disabled = false;
      console.warn('[Acassia Webchat] Erro ao enviar:', err);
    }
  }

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendMessage();
    }
  });
  sendBtn.addEventListener('click', sendMessage);

  // 7. Polling para mensagens do atendente humano
  function startPolling() {
    if (pollInterval) return;
    pollInterval = setInterval(async () => {
      if (!isOpen || !sessionId) return;
      try {
        const res = await fetch(`${apiBase}/api/public/webchat/poll?tenant_id=${tenantId}&session_id=${sessionId}&after_id=${lastMessageId}`);
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
          data.messages.forEach(m => {
            if (m.sender === 'assistant') {
              appendMessage(m.text, 'assistant');
            }
            if (m.id > lastMessageId) lastMessageId = m.id;
          });
        }
      } catch {}
    }, 4000);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }
})();
