import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Activity, AudioLines, Hash, MessageCircle, Send, Users, Wifi, WifiOff, Zap } from "lucide-react";

type ChatMessage = {
  id?: number;
  type: "message";
  username: string;
  text: string;
  created_at?: string;
};

type ServerError = {
  type: "error";
  message: string;
};

type FeedItem = ChatMessage | ServerError;

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws/chat";

const starterMessages: ChatMessage[] = [
  { type: "message", username: "System", text: "Welcome to Community Live! Be kind and enjoy the conversation." }
];

function initials(name: string): string {
  return name.slice(0, 2).toUpperCase();
}

export default function App() {
  const [username, setUsername] = useState("Guest");
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>(starterMessages);
  const [connected, setConnected] = useState(false);
  const [notice, setNotice] = useState("Connecting to the community…");
  const socketRef = useRef<WebSocket | null>(null);
  const feedRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`${API_URL}/api/messages?limit=50`)
      .then((response) => {
        if (!response.ok) throw new Error("Unable to load chat history.");
        return response.json() as Promise<ChatMessage[]>;
      })
      .then((history) => {
        if (active && history.length) {
          setMessages((current) => {
            const merged = new Map<number, ChatMessage>();
            current.forEach((item) => {
              if (item.id !== undefined) merged.set(item.id, item);
            });
            history.forEach((item) => {
              if (item.id !== undefined) merged.set(item.id, item);
            });
            return [...merged.values()].sort((a, b) => (a.id ?? 0) - (b.id ?? 0));
          });
        }
      })
      .catch(() => {
        if (active) setNotice("Chat history is unavailable. You can still try connecting.");
      });

    const socket = new WebSocket(WS_URL);
    socketRef.current = socket;

    socket.onopen = () => {
      setConnected(true);
      setNotice("You're connected. Say hello!");
    };
    socket.onmessage = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as FeedItem;
        if (payload.type === "message") {
          setMessages((current) => {
            if (payload.id && current.some((item) => item.id === payload.id)) return current;
            return [...current, payload];
          });
        } else {
          setNotice(payload.message);
        }
      } catch {
        setNotice("Received an unreadable message from the server.");
      }
    };
    socket.onerror = () => setNotice("Connection problem. Check that the API is running.");
    socket.onclose = () => {
      setConnected(false);
      setNotice("Disconnected from chat. Refresh to reconnect.");
    };

    return () => {
      active = false;
      socket.close();
      socketRef.current = null;
    };
  }, []);

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const participantCount = useMemo(() => connected ? 1 : 0, [connected]);

  function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    const name = username.trim();

    if (!text || !name || text.length > 500 || name.length > 24) {
      setNotice("Use a name (1–24 characters) and a message (1–500 characters).");
      return;
    }

    if (socketRef.current?.readyState !== WebSocket.OPEN) {
      setNotice("Chat is offline. Start the API and refresh the page.");
      return;
    }

    socketRef.current.send(JSON.stringify({ username: name, text }));
    setDraft("");
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Community Live home">
          <span className="brand-mark"><AudioLines size={21} /></span>
          <span>community<span className="brand-accent">live</span></span>
        </a>
        <div className="topbar-right">
          <span className="live-indicator"><span /> LIVE ROOM</span>
          <span className="avatar avatar-you">V</span>
        </div>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><Zap size={14} /> YOUR COMMUNITY, IN REAL TIME</div>
          <h1>Find your people.<br /><span>Start a conversation.</span></h1>
          <p>A welcoming space to share ideas, meet makers, and build something together.</p>
          <div className="hero-stats">
            <div><strong>{participantCount.toString().padStart(2, "0")}</strong><span>you connected</span></div>
            <div className="stat-divider" />
            <div><strong>01</strong><span>community room</span></div>
            <div className="stat-divider" />
            <div><strong>24/7</strong><span>good conversations</span></div>
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit orbit-one" /><div className="orbit orbit-two" />
          <div className="orb orb-main"><AudioLines size={54} /></div>
          <div className="orb orb-small orb-a"><MessageCircle size={21} /></div>
          <div className="orb orb-small orb-b"><Users size={22} /></div>
          <div className="orb orb-small orb-c"><Activity size={20} /></div>
          <span className="art-dot dot-a" /><span className="art-dot dot-b" />
        </div>
      </section>

      <section className="workspace">
        <aside className="rooms-panel">
          <div className="panel-heading">YOUR SPACES <span>01</span></div>
          <button className="room-item selected"><Hash size={17} /><span><strong>general</strong><small>Meet the community</small></span><i /></button>
          <div className="room-note"><div className="note-icon"><Users size={18} /></div><strong>Good vibes only</strong><p>Make space for new voices. Keep it friendly and respectful.</p></div>
          <div className="connection-card">
            <div className="connection-title">{connected ? <Wifi size={15} /> : <WifiOff size={15} />} CONNECTION</div>
            <span className={connected ? "status-online" : "status-offline"}>{connected ? "Connected" : "Offline"}</span>
            <small>{notice}</small>
          </div>
        </aside>

        <section className="chat-panel">
          <div className="chat-header">
            <div><div className="chat-title"><Hash size={18} /> general</div><p>The place where every conversation starts.</p></div>
            <div className="chat-presence"><span className={connected ? "presence-dot" : "presence-dot offline"} /> {participantCount} online</div>
          </div>
          <div className="message-feed" ref={feedRef} aria-live="polite">
            <div className="day-divider"><span /> CHAT HISTORY <span /></div>
            {messages.map((message, index) => (
              <article className="message" key={message.id ?? index}>
                <div className={message.username === "System" ? "avatar system-avatar" : "avatar"}>{initials(message.username)}</div>
                <div className="message-content">
                  <div className="message-meta"><strong>{message.username}</strong><time>{message.created_at ? new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "WELCOME"}</time></div>
                  <p>{message.text}</p>
                </div>
              </article>
            ))}
          </div>
          <form className="composer" onSubmit={sendMessage}>
            <label className="sr-only" htmlFor="username">Display name</label>
            <input id="username" className="name-input" value={username} maxLength={24} onChange={(event) => setUsername(event.target.value)} aria-label="Display name" />
            <label className="sr-only" htmlFor="message">Write a message</label>
            <input id="message" value={draft} maxLength={500} onChange={(event) => setDraft(event.target.value)} placeholder="Share something with the community…" />
            <button type="submit" disabled={!connected || !draft.trim()} aria-label="Send message"><Send size={17} /></button>
          </form>
          <div className="composer-hint">Be thoughtful. Your message is shared with everyone in this room.</div>
        </section>

        <aside className="about-panel">
          <div className="panel-heading">ROOM DETAILS</div>
          <div className="room-cover"><div className="cover-glow" /><AudioLines size={36} /></div>
          <h3>General chat</h3><p className="about-description">An open room for introductions, questions, ideas, and everyday conversations.</p>
          <div className="about-row"><Users size={16} /><span>Community room</span></div>
          <div className="about-row"><MessageCircle size={16} /><span>Real-time messaging</span></div>
          <div className="about-row"><Activity size={16} /><span>Built for good conversations</span></div>
          <div className="about-footer"><span className="footer-pulse" /> Powered by WebSockets</div>
        </aside>
      </section>
      <footer className="footer"><span>COMMUNITY LIVE</span><span>Built for connection, designed for conversation.</span><span>V 0.2.0</span></footer>
    </main>
  );
}
