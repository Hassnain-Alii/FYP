/**
 * AI Chat Agent - Core Frontend Logic (Revamped)
 */

let currentSessionId = null;
let isTyping = false;
let freeLimit = 100;
let renamingConvId = null;

async function initChat() {
  loadUsageStats();
  
  const lastSessionId = localStorage.getItem('lastSessionId');
  
  try {
    const response = await fetch("/api/conversations");
    const data = await response.json();
    
    let loaded = false;
    if (data.conversations && data.conversations.length > 0) {
      const exists = data.conversations.find(c => c.session_id === lastSessionId);
      if (exists) {
        await loadConversation(lastSessionId);
        loaded = true;
      } else {
        await loadConversation(data.conversations[0].session_id);
        loaded = true;
      }
    }
    
    if (!loaded) {
      startNewChat();
      loadConversations();
    }
  } catch (e) {
    startNewChat();
    loadConversations();
  }

  const input = document.getElementById("messageInput");
  if (input) input.focus();

  // Close modal or sidebar on outside click
  window.onclick = function(event) {
    const modal = document.getElementById("renameModal");
    const sidebar = document.getElementById("sidebar");
    
    // Handle Modal
    if (event.target == modal) {
      closeRenameModal();
    }

    // Handle Mobile Sidebar Close on Click Outside
    if (window.innerWidth <= 768 && 
        sidebar.classList.contains("open") && 
        !sidebar.contains(event.target) && 
        !event.target.closest(".mobile-toggle")) {
      sidebar.classList.remove("open");
    }
  }
}

function toggleSidebar(event) {
  if (event) event.stopPropagation();
  const sidebar = document.getElementById("sidebar");
  sidebar.classList.toggle("open");
}

function startNewChat() {
  currentSessionId = generateSessionId();
  localStorage.setItem('lastSessionId', currentSessionId);
  document.getElementById("currentChatTitle").textContent = "🤖 New Chat";

  const messagesContainer = document.getElementById("chatMessages");
  messagesContainer.innerHTML = `
        <div class="message assistant welcome-message">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="message-bubble">
                    <p>Hello! 👋 I'm your AI assistant. How can I help you today?</p>
                </div>
                <span class="message-time">System</span>
            </div>
        </div>
    `;
}

function generateSessionId() {
  return "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
}

async function sendMessage(event) {
  event.preventDefault();

  const input = document.getElementById("messageInput");
  const message = input.value.trim();

  if (!message || isTyping) return;

  const usageCount = parseInt(document.getElementById("usageCount").textContent);
  if (usageCount >= freeLimit) {
    showLimitOverlay();
    return;
  }

  input.value = "";
  autoResize(input);
  addMessage("user", message);
  showTypingIndicator();
  isTyping = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        session_id: currentSessionId,
      }),
    });

    const data = await response.json();
    hideTypingIndicator();
    isTyping = false;

    if (response.status === 429) {
      showLimitOverlay();
      return;
    }

    if (!response.ok) {
      addMessage("assistant", "Error: " + (data.error || "Server issue"));
      return;
    }

    addMessage("assistant", data.response);
    updateUsageDisplay(data.daily_count, data.limit, data.remaining);
    
    // Refresh sidebar to show the first message as title if needed
    loadConversations();
  } catch (error) {
    console.error("Chat Error:", error);
    hideTypingIndicator();
    isTyping = false;
    addMessage("assistant", "Network Error: Server unreachable.");
  }
}

function addMessage(role, content) {
  const messagesContainer = document.getElementById("chatMessages");
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${role}`;

  const avatar = role === "user" ? "👤" : "🤖";
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
  
  const formattedContent = escapeHtml(content).replace(/\n/g, "<br>");

  messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-bubble">
                <p>${formattedContent}</p>
            </div>
            <span class="message-time">${time}</span>
        </div>
    `;

  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showTypingIndicator() {
  const messagesContainer = document.getElementById("chatMessages");
  const typingDiv = document.createElement("div");
  typingDiv.className = "message assistant";
  typingDiv.id = "typingIndicator";

  typingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>
        </div>
    `;

  messagesContainer.appendChild(typingDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideTypingIndicator() {
  const el = document.getElementById("typingIndicator");
  if (el) el.remove();
}

async function loadUsageStats() {
  try {
    const response = await fetch("/api/usage");
    const data = await response.json();
    freeLimit = data.limit;
    updateUsageDisplay(data.daily_count, data.limit, data.remaining);
    if (!data.can_send) showLimitOverlay();
  } catch (e) {}
}

function updateUsageDisplay(count, limit, remaining) {
  document.getElementById("usageBar").style.width = `${(count / limit) * 100}%`;
  document.getElementById("usageCount").textContent = count;
  document.getElementById("usageLimit").textContent = limit;
  document.getElementById("usageRemaining").textContent = `${remaining} messages left today`;
}

function showLimitOverlay() {
  document.getElementById("limitOverlay").style.display = "flex";
  document.getElementById("messageInput").disabled = true;
  document.getElementById("sendBtn").disabled = true;
}

async function loadConversations() {
  try {
    const response = await fetch("/api/conversations");
    const data = await response.json();
    const listContainer = document.getElementById("conversationList");

    if (data.conversations.length === 0) {
      listContainer.innerHTML = '<p class="empty-msg">No chats yet</p>';
      return;
    }

    listContainer.innerHTML = data.conversations
      .map(conv => {
        const title = conv.title || `Chat ${formatDate(conv.created_at)}`;
        const activeClass = conv.session_id === currentSessionId ? "active" : "";
        return `
            <div class="conversation-item ${activeClass}" onclick="loadConversation('${conv.session_id}')">
                <div class="conv-title">${title}</div>
                <div class="menu-trigger" onclick="event.stopPropagation(); openRenameModal(${conv.id}, '${title}')">⋮</div>
            </div>
        `;
      })
      .join("");
  } catch (e) {}
}

async function loadConversation(sessionId) {
  try {
    const response = await fetch(`/api/conversations/${sessionId}`);
    const data = await response.json();
    if (response.ok) {
      currentSessionId = sessionId;
      localStorage.setItem('lastSessionId', currentSessionId);
      const messagesContainer = document.getElementById("chatMessages");
      messagesContainer.innerHTML = "";
      data.messages.forEach(msg => addMessage(msg.role, msg.content));
      
      // Update Title
      const title = data.title || `Chat ${formatDate(data.created_at)}`;
      document.getElementById("currentChatTitle").textContent = "🤖 " + title;
      
      // Close sidebar on mobile
      if (window.innerWidth <= 768) toggleSidebar();
      
      // Update active state in sidebar
      loadConversations();
    }
  } catch (e) {}
}

// RENAME LOGIC
function openRenameModal(id, currentTitle) {
  renamingConvId = id;
  const modal = document.getElementById("renameModal");
  const input = document.getElementById("newChatName");
  input.value = currentTitle;
  modal.style.display = "flex";
  input.focus();
}

function closeRenameModal() {
  document.getElementById("renameModal").style.display = "none";
  renamingConvId = null;
}

async function saveNewName() {
  const newTitle = document.getElementById("newChatName").value.trim();
  if (!newTitle || !renamingConvId) return;

  try {
    const response = await fetch(`/api/conversations/${renamingConvId}/rename`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: newTitle }),
    });

    if (response.ok) {
      closeRenameModal();
      loadConversations();
      // If renaming the active chat, update main header
      if (currentSessionId) {
          document.getElementById("currentChatTitle").textContent = "🤖 " + newTitle;
      }
    }
  } catch (e) {
    console.error("Rename failed", e);
  }
}

// UTILS
function handleKeyDown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    document.getElementById("chatForm").dispatchEvent(new Event("submit"));
  }
}

function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + "px";
}

function formatDate(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return date.toLocaleDateString();
}

document.addEventListener("DOMContentLoaded", initChat);
