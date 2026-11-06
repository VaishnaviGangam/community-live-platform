import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Activity, AudioLines, Hash, LogOut, MessageCircle, Send, Users, Wifi, WifiOff, Zap } from "lucide-react";

type User = { id: number; username: string; email: string; created_at: string };
type ChatMessage = { id?: number; type: "message"; username: string; text: string; created_at?: string };
type ServerError = { type: "error"; message: string };
type FeedItem = ChatMessage | ServerError;
type AuthResponse = { access_token: string; token_type: string; user: User };

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws/chat";
const starterMessages: ChatMessage[] = [
  { type: "message", username: "System", text: "Welcome to Community Live! Be kind and enjoy the conversation." }
];

function initials(name: string): string { return name.slice(0, 2).toUpperCase(); }

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("community_live_token"));
  const [authMode, setAuthMode] = useState<"login" | "register">("register");
  const [authName, setAuthName] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState("");
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>(starterMessages);
  const [connected, setConnected] = useState(false);
  const [notice, setNotice] = useState("Connect to join the community.");
  const socketRef = useRef<WebSocket | null>(null);
  const feedRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!token) { setUser(null); return; }
    fetch(`${API_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error("Your session expired. Please sign in again.");
        return response.json() as Promise<User>;
      })
      .then(setUser)
      .catch((error: Error) => {
        localStorage.removeItem("community_live_token");
        setToken(null);
        setUser(null);
        setAuthError(error.message);
      });
  }, [token]);

  useEffect(() => {
    if (!token || !user) return;
    let active = true;
    fetch(`${API_URL}/api/messages?limit=50`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        if (!response.ok) throw new Error("Unable to load chat history.");
        return response.json() as Promise<ChatMessage[]>;
      })
      .then((history) => {
        if (active && history.length) {
          setMessages((current) => {
            const merged = new Map<number, ChatMessage>();
            current.forEach((item) => { if (item.id !== undefined) merged.set(item.id, item); });
            history.forEach((item) => { if (item.id !== undefined) merged.set(item.id, item); });
            return [...merged.values()].sort((a, b) => (a.id ?? 0) - (b.id ?? 0));
          });
        }
      })
      .catch(() => { if (active) setNotice("Chat history is unavailable. You can still chat."); });

    const socket = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
    socketRef.current = socket;
    socket.onopen = () => { setConnected(true); setNotice("You're connected. Say hello!"); };
    socket.onmessage = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as FeedItem;
        if (payload.type === "message") {
          setMessages((current) => {
            if (payload.id && current.some((item) => item.id === payload.id)) return current;
            return [...current, payload];
          });
        } else setNotice(payload.message);
      } catch { setNotice("Received an unreadable message from the server."); }
    };
    socket.onerror = () => setNotice("Connection problem. Check that the API is running.");
    socket.onclose = (event) => {
      setConnected(false);
      if (event.code === 4401) {
        localStorage.removeItem("community_live_token");
        setToken(null);
        setUser(null);
        setAuthError("Your session is no longer valid. Please sign in again.");
      } else setNotice("Disconnected from chat. Refresh to reconnect.");
    };
    return () => {
      active = false;
      socket.close();
      socketRef.current = null;
    };
  }, [token, user]);

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const participantCount = useMemo(() => connected ? 1 : 0, [connected]);

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    try {
      const endpoint = authMode === "register" ? "/api/auth/register" : "/api/auth/login";
      const payload = authMode === "register"
        ? { username: authName.trim(), email: authEmail.trim(), password: authPassword }
        : { email: authEmail.trim(), password: authPassword };
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await response.json() as AuthResponse | { detail?: string };
      if (!response.ok) throw new Error("detail" in result ? result.detail ?? "Unable to authenticate." : "Unable to authenticate.");
      const auth = result as AuthResponse;
      localStorage.setItem("community_live_token", auth.access_token);
      setToken(auth.access_token);
      setUser(auth.user);
      setAuthPassword("");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Something went wrong. Please try again.");
    } finally { setAuthBusy(false); }
  }

  function logout() {
    socketRef.current?.close();
    localStorage.removeItem("community_live_token");
    setToken(null);
    setUser(null);
    setMessages(starterMessages);
    setConnected(false);
    setNotice("You have signed out.");
  }

  function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || text.length > 500) { setNotice("Enter a message between 1 and 500 characters."); return; }
    if (socketRef.current?.readyState !== WebSocket.OPEN) { setNotice("Chat is offline. Refresh to reconnect."); return; }
    socketRef.current.send(JSON.stringify({ text }));
    setDraft("");
  }

  if (!user || !token) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <a className="brand auth-brand" href="/"><span className="brand-mark"><AudioLines size={21} /></span><span>community<span className="brand-accent">live</span></span></a>
          <div className="auth-eyebrow"><Zap size={14} /> YOUR COMMUNITY, IN REAL TIME</div>
          <h1>{authMode === "register" ? "Find your people." : "Welcome back."}</h1>
          <p className="auth-subtitle">{authMode === "register" ? "Create an account to join conversations and meet your community." : "Sign in to pick up where the conversation left off."}</p>
          <div className="auth-tabs">
            <button type="button" className={authMode === "register" ? "active" : ""} onClick={() => { setAuthMode("register"); setAuthError(""); }}>Create account</button>
            <button type="button" className={authMode === "login" ? "active" : ""} onClick={() => { setAuthMode("login"); setAuthError(""); }}>Sign in</button>
          </div>
          <form className="auth-form" onSubmit={submitAuth}>
            {authMode === "register" && <label>Username<input value={authName} onChange={(event) => setAuthName(event.target.value)} minLength={3} maxLength={24} pattern="[A-Za-z0-9_]+" placeholder="e.g. vaishnavi" autoComplete="username" required /></label>}
            <label>Email address<input type="email" value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} placeholder="you@example.com" autoComplete="email" required /></label>
            <label>Password<input type="password" value={authPassword} onChange={(event) => setAuthPassword(event.target.value)} minLength={authMode === "register" ? 10 : 1} maxLength={128} placeholder={authMode === "register" ? "At least 10 characters" : "Your password"} autoComplete={authMode === "register" ? "new-password" : "current-password"} required /></label>
            {authMode === "register" && <small className="password-hint">Use at least 10 characters. Your password is securely hashed before storage.</small>}
            {authError && <div className="auth-error" role="alert">{authError}</div>}
            <button className="auth-submit" type="submit" disabled={authBusy}>{authBusy ? "Please wait…" : authMode === "register" ? "Create your account" : "Sign in"} <span>→</span></button>
          </form>
          <div className="auth-footnote"><span className="footer-pulse" /> Secure account access · Community Live</div>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Community Live home"><span className="brand-mark"><AudioLines size={21} /></span><span>community<span className="brand-accent">live</span></span></a>
        <div className="topbar-right"><span className="live-indicator"><span /> LIVE ROOM</span><span className="avatar avatar-you">{initials(user.username)}</span><span className="signed-in-name">{user.username}</span><button className="logout-button" onClick={logout} title="Sign out"><LogOut size={16} /></button></div>
      </header>
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><Zap size={14} /> YOUR COMMUNITY, IN REAL TIME</div>
          <h1>Find your people.<br /><span>Start a conversation.</span></h1>
          <p>A welcoming space to share ideas, meet makers, and build something together.</p>
          <div className="hero-stats"><div><strong>{participantCount.toString().padStart(2, "0")}</strong><span>you connected</span></div><div className="stat-divider" /><div><strong>01</strong><span>community room</span></div><div className="stat-divider" /><div><strong>24/7</strong><span>good conversations</span></div></div>
        </div>
        <div className="hero-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orb orb-main"><AudioLines size={54} /></div><div className="orb orb-small orb-a"><MessageCircle size={21} /></div><div className="orb orb-small orb-b"><Users size={22} /></div><div className="orb orb-small orb-c"><Activity size={20} /></div><span className="art-dot dot-a" /><span className="art-dot dot-b" /></div>
      </section>
      <section className="workspace">
        <aside className="rooms-panel">
          <div className="panel-heading">YOUR SPACES <span>01</span></div>
          <button className="room-item selected"><Hash size={17} /><span><strong>general</strong><small>Meet the community</small></span><i /></button>
          <div className="room-note"><div className="note-icon"><Users size={18} /></div><strong>Good vibes only</strong><p>Make space for new voices. Keep it friendly and respectful.</p></div>
          <div className="connection-card"><div className="connection-title">{connected ? <Wifi size={15} /> : <WifiOff size={15} />} CONNECTION</div><span className={connected ? "status-online" : "status-offline"}>{connected ? "Connected" : "Offline"}</span><small>{notice}</small></div>
        </aside>
        <section className="chat-panel">
          <div className="chat-header"><div><div className="chat-title"><Hash size={18} /> general</div><p>The place where every conversation starts.</p></div><div className="chat-presence"><span className={connected ? "presence-dot" : "presence-dot offline"} /> {participantCount} online</div></div>
          <div className="message-feed" ref={feedRef} aria-live="polite"><div className="day-divider"><span /> CHAT HISTORY <span /></div>
            {messages.map((message, index) => <article className="message" key={message.id ?? index}><div className={message.username === "System" ? "avatar system-avatar" : "avatar"}>{initials(message.username)}</div><div className="message-content"><div className="message-meta"><strong>{message.username}</strong><time>{message.created_at ? new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "WELCOME"}</time></div><p>{message.text}</p></div></article>)}
          </div>
          <form className="composer" onSubmit={sendMessage}><span className="name-input signed-user-label">{user.username}</span><label className="sr-only" htmlFor="message">Write a message</label><input id="message" value={draft} maxLength={500} onChange={(event) => setDraft(event.target.value)} placeholder="Share something with the community…" /><button type="submit" disabled={!connected || !draft.trim()} aria-label="Send message"><Send size={17} /></button></form>
          <div className="composer-hint">Signed in as {user.email}. Your message is shared with everyone in this room.</div>
        </section>
        <aside className="about-panel"><div className="panel-heading">ROOM DETAILS</div><div className="room-cover"><div className="cover-glow" /><AudioLines size={36} /></div><h3>General chat</h3><p className="about-description">An open room for introductions, questions, ideas, and everyday conversations.</p><div className="about-row"><Users size={16} /><span>Community room</span></div><div className="about-row"><MessageCircle size={16} /><span>Authenticated real-time messaging</span></div><div className="about-row"><Activity size={16} /><span>Built for good conversations</span></div><div className="about-footer"><span className="footer-pulse" /> Powered by WebSockets</div></aside>
      </section>
      <footer className="footer"><span>COMMUNITY LIVE</span><span>Built for connection, designed for conversation.</span><span>V 0.3.0</span></footer>
    </main>
  );
}
