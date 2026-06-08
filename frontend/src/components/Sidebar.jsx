import { useState, useEffect } from "react"
import { useAuth } from "../context/AuthContext"

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

/**
 * Sidebar — shows chat session history and lets the user
 * create a new session or switch between past ones.
 */
export default function Sidebar({ activeSessionId, onSelectSession, onNewChat, refreshTrigger }) {

    const { token, user, logout } = useAuth()
    const [sessions, setSessions]   = useState([])
    const [loading,  setLoading]    = useState(true)

    useEffect(() => {
        fetchSessions()
    }, [activeSessionId, refreshTrigger])   // refresh when a new session is created or title updates

    async function fetchSessions() {
        setLoading(true)
        try {
            const res  = await fetch(`${API}/history/sessions`, {
                headers: { Authorization: `Bearer ${token}` },
            })
            const data = await res.json()
            setSessions(Array.isArray(data) ? data : [])
        } catch {
            setSessions([])
        } finally {
            setLoading(false)
        }
    }

    async function handleNewChat() {
        try {
            const res  = await fetch(`${API}/history/session`, {
                method:  "POST",
                headers: { Authorization: `Bearer ${token}` },
            })
            const data = await res.json()
            onNewChat(data.session_id)
            fetchSessions()
        } catch (err) {
            console.error("Failed to create session:", err)
        }
    }

    function formatDate(dateStr) {
        if (!dateStr) return ""
        const d = new Date(dateStr)
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
    }

    return (
        <div className="
            w-64 h-full bg-white/5 backdrop-blur-3xl
            border-r border-white/5
            flex flex-col
            shadow-[4px_0_24px_rgba(0,0,0,0.2)]
            relative z-20
        ">

            {/* Brand */}
            <div className="p-5 border-b border-white/5 shadow-sm">
                <h1 className="text-xl font-bold text-white tracking-wide">
                    Ops<span className="text-blue-400">Pilot</span> AI
                </h1>
                <p className="text-gray-400 text-xs mt-0.5 tracking-wider uppercase font-medium">Agentic AI Platform</p>
            </div>

            {/* New Chat Button */}
            <div className="p-3">
                <button
                    id="new-chat-btn"
                    onClick={handleNewChat}
                    className="
                        w-full flex items-center gap-2
                        bg-white/5 hover:bg-white/10
                        border border-white/10 hover:border-blue-400/50
                        text-gray-200 text-sm font-medium
                        rounded-xl px-4 py-2.5 transition-all duration-200
                        shadow-sm hover:shadow-[0_0_15px_rgba(59,130,246,0.3)]
                    "
                >
                    <span className="text-lg text-blue-400">＋</span>
                    New Chat
                </button>
            </div>

            {/* Session List */}
            <div className="flex-1 overflow-y-auto px-2 pb-4">

                {loading ? (
                    <div className="text-center text-gray-600 text-xs py-6">Loading sessions…</div>
                ) : sessions.length === 0 ? (
                    <div className="text-center text-gray-600 text-xs py-6">No sessions yet</div>
                ) : (
                    <div className="space-y-1">
                        <p className="text-gray-600 text-xs px-2 py-2 uppercase tracking-wider">
                            Recent Chats
                        </p>
                        {sessions.map(session => (
                            <div key={session.id} className="relative group flex items-center">
                                <button
                                    onClick={() => onSelectSession(session.id)}
                                    className={`
                                        w-full text-left px-3 py-2.5 rounded-xl text-sm transition-all duration-200
                                        flex items-start gap-2 group pr-8
                                        ${activeSessionId === session.id
                                            ? "bg-blue-600/20 text-white border border-blue-400/30 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]"
                                            : "text-gray-400 hover:bg-white/10 hover:text-white border border-transparent"
                                        }
                                    `}
                                >
                                    <span className="mt-0.5 opacity-60">💬</span>
                                    <span className="flex-1 truncate">
                                        {session.title || `Chat #${session.id}`}
                                    </span>
                                </button>
                                <button
                                    onClick={async (e) => {
                                        e.stopPropagation();
                                        if (!confirm("Delete this conversation?")) return;
                                        try {
                                            await fetch(`${API}/history/session/${session.id}`, {
                                                method: "DELETE",
                                                headers: { Authorization: `Bearer ${token}` }
                                            });
                                            if (activeSessionId === session.id) onSelectSession(null);
                                            fetchSessions();
                                        } catch (err) {
                                            console.error("Delete failed", err);
                                        }
                                    }}
                                    className="absolute right-2 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition p-1"
                                    title="Delete Conversation"
                                >
                                    🗑️
                                </button>
                            </div>
                        ))}
                    </div>
                )}

            </div>

            {/* User Footer */}
            <div className="border-t border-white/5 p-4 flex items-center gap-3 bg-white/[0.02]">

                <div className="
                    w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600
                    flex items-center justify-center
                    text-white text-sm font-bold shrink-0
                    shadow-[0_0_10px_rgba(59,130,246,0.5)]
                ">
                    {user?.email?.[0]?.toUpperCase() || "U"}
                </div>

                <div className="flex-1 min-w-0">
                    <p className="text-gray-200 text-sm truncate font-medium">{user?.full_name || user?.email}</p>
                    <p className="text-gray-400 text-xs truncate">{user?.email}</p>
                </div>

                <button
                    id="logout-btn"
                    onClick={logout}
                    title="Sign out"
                    className="text-gray-400 hover:text-red-400 transition-colors text-sm p-1.5 hover:bg-white/5 rounded-lg"
                >
                    ⏻
                </button>

            </div>

        </div>
    )
}
