// API paths are relative because FastAPI serves this frontend.
const CHAT_API = "/api/chat";
const USER_API = "/api/users";

// Keep session history in this browser.
const STORAGE_KEY = "project_tracking_sessions";
const COUNTER_KEY = "project_tracking_session_counter";

let sessions = loadSessions();
let activeSessionId = sessions.length ? sessions[0].id : null;
let isSending = false;

// ---------- Session management ----------

function loadSessions() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    } catch {
        return [];
    }
}

function saveSessions() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

function createSessionId() {
    const nextNumber = Number(localStorage.getItem(COUNTER_KEY) || "0") + 1;
    localStorage.setItem(COUNTER_KEY, String(nextNumber));
    return `testing-${String(nextNumber).padStart(3, "0")}`;
}

function createSession() {
    const session = {
        id: createSessionId(),
        title: "New conversation",
        messages: []
    };

    sessions.unshift(session);
    activeSessionId = session.id;
    saveSessions();
    renderSessions();
    renderActiveSession();
}

function getActiveSession() {
    return sessions.find(session => session.id === activeSessionId);
}

function renderSessions() {
    const list = document.getElementById("session-list");
    list.innerHTML = "";

    sessions.forEach(session => {
        const button = document.createElement("button");
        button.className = "session-item";
        if (session.id === activeSessionId) button.classList.add("active");

        button.textContent = session.id;
        button.title = session.title;
        button.addEventListener("click", () => {
            activeSessionId = session.id;
            renderSessions();
            renderActiveSession();
        });

        list.appendChild(button);
    });
}

function renderActiveSession() {
    const session = getActiveSession();
    const title = document.getElementById("current-session-title");
    const subtitle = document.getElementById("current-session-id");
    const messages = document.getElementById("messages");

    messages.innerHTML = "";

    if (!session) {
        title.textContent = "New conversation";
        subtitle.textContent = "Create a session to start chatting.";
        showWelcome(messages);
        return;
    }

    title.textContent = session.title;
    subtitle.textContent = `Session ID: ${session.id}`;

    if (session.messages.length === 0) {
        showWelcome(messages);
        return;
    }

    session.messages.forEach(message => {
        addMessageToScreen(message.role, message.content, false);
    });

    scrollToBottom();
}

function showWelcome(container) {
    const welcome = document.createElement("div");
    welcome.className = "welcome";
    welcome.innerHTML = `
        <div class="welcome-icon">PT</div>
        <h2>Project Tracking Agent</h2>
        <p>Ask questions about GitHub repositories, issues, pull requests, Linear projects, and teams.</p>
        <div class="suggestions">
            <button class="suggestion">Show my GitHub repositories</button>
            <button class="suggestion">Show my open pull requests</button>
            <button class="suggestion">List my Linear projects</button>
        </div>
    `;

    welcome.querySelectorAll(".suggestion").forEach(button => {
        button.addEventListener("click", () => {
            document.getElementById("chat-input").value = button.textContent;
            document.getElementById("chat-input").focus();
        });
    });

    container.appendChild(welcome);
}

// ---------- Chat messages ----------

function addMessageToScreen(role, content, shouldScroll = true, isError = false) {
    const container = document.getElementById("messages");
    const welcome = container.querySelector(".welcome");
    if (welcome) welcome.remove();

    const message = document.createElement("div");
    message.className = `message ${role}`;
    if (isError) message.classList.add("error");

    const label = document.createElement("div");
    label.className = "message-role";
    label.textContent = role === "user" ? "YOU" : "AGENT";

    const body = document.createElement("div");
    body.className = "message-content";
    // textContent prevents agent responses from being interpreted as HTML.
    body.textContent = content;

    message.append(label, body);
    container.appendChild(message);

    if (shouldScroll) scrollToBottom();
}

function addMessage(role, content) {
    const session = getActiveSession();
    if (!session) return;

    session.messages.push({ role, content });
    saveSessions();
    addMessageToScreen(role, content);
}

function scrollToBottom() {
    const container = document.getElementById("messages");
    container.scrollTop = container.scrollHeight;
}

function setSending(sending) {
    isSending = sending;
    document.getElementById("send-btn").disabled = sending;
    document.getElementById("send-btn").textContent = sending ? "Sending..." : "Send";
}

// ---------- Chat API ----------

async function sendMessage(event) {
    event.preventDefault();

    if (isSending) return;

    const input = document.getElementById("chat-input");
    const query = input.value.trim();

    if (!query) return;

    if (!activeSessionId) createSession();

    const session = getActiveSession();
    if (!session) return;

    input.value = "";

    if (session.messages.length === 0) {
        session.title = query.length > 35 ? `${query.slice(0, 35)}...` : query;
        renderSessions();
        renderActiveSession();
    }

    addMessage("user", query);
    setSending(true);

    try {
        const response = await fetch(CHAT_API, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                query: query,
                thread_id: session.id
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Chat request failed.");
        }

        addMessage("assistant", result.response || "The agent returned an empty response.");

    } catch (error) {
        addMessage("assistant", `Request failed: ${error.message}`);
    } finally {
        setSending(false);
        input.focus();
    }
}

// ---------- User creation modal ----------

function openUserModal() {
    document.getElementById("user-modal").classList.remove("hidden");
    clearUserFormMessages();
}

function closeUserModal() {
    document.getElementById("user-modal").classList.add("hidden");
}

function clearUserFormMessages() {
    document.getElementById("user-form-error").textContent = "";
    document.getElementById("user-form-success").textContent = "";
}

async function createUser(event) {
    event.preventDefault();
    clearUserFormMessages();

    const name = document.getElementById("user-name").value.trim();
    const email = document.getElementById("user-email").value.trim();
    const githubSecret = document.getElementById("github-secret").value.trim();
    const linearSecret = document.getElementById("linear-secret").value.trim();

    const integrations = [];

    if (githubSecret) {
        integrations.push({
            provider: "GITHUB",
            secret: githubSecret
        });
    }

    if (linearSecret) {
        integrations.push({
            provider: "LINEAR",
            secret: linearSecret
        });
    }

    if (integrations.length === 0) {
        document.getElementById("user-form-error").textContent =
            "Add at least one GitHub or Linear credential.";
        return;
    }

    const button = document.getElementById("create-user-btn");
    button.disabled = true;
    button.textContent = "Creating...";

    try {
        const response = await fetch(USER_API, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name,
                email,
                integrations
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Unable to create user.");
        }

        document.getElementById("user-form-success").textContent =
            `User ${result.name} created successfully.`;

        document.getElementById("user-form").reset();

        // Close after a short delay so the success message can be seen.
        setTimeout(closeUserModal, 900);

    } catch (error) {
        document.getElementById("user-form-error").textContent = error.message;
    } finally {
        button.disabled = false;
        button.textContent = "Create user";
    }
}

// ---------- Backend health check ----------

async function checkBackend() {
    const status = document.getElementById("connection-status");
    const dot = document.querySelector(".status-dot");

    try {
        const response = await fetch("/health");
        if (!response.ok) throw new Error("Backend unavailable");

        status.textContent = "Connected";
        dot.style.background = "#2d9b68";
    } catch {
        status.textContent = "Disconnected";
        dot.style.background = "#cf5148";
    }
}

// ---------- Event listeners ----------

document.getElementById("new-session-btn").addEventListener("click", createSession);
document.getElementById("chat-form").addEventListener("submit", sendMessage);
document.getElementById("open-user-modal").addEventListener("click", openUserModal);
document.getElementById("close-user-modal").addEventListener("click", closeUserModal);
document.getElementById("cancel-user").addEventListener("click", closeUserModal);
document.getElementById("modal-backdrop").addEventListener("click", closeUserModal);
document.getElementById("user-form").addEventListener("submit", createUser);

// Enter sends; Shift + Enter inserts a new line.
document.getElementById("chat-input").addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        document.getElementById("chat-form").requestSubmit();
    }
});

// ---------- Start application ----------

if (!activeSessionId) {
    createSession();
} else {
    renderSessions();
    renderActiveSession();
}

checkBackend();
