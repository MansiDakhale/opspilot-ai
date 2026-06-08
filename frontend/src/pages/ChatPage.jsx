import { useState, useEffect, useRef } from "react"
import ReactMarkdown from "react-markdown"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { atomDark } from "react-syntax-highlighter/dist/esm/styles/prism"
import FileUpload    from "../components/FileUpload"
import { useAuth }   from "../context/AuthContext"

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

export default function ChatPage({ sessionId, onSessionCreated, onTitleUpdated }) {

    const { token }                           = useAuth()
    const [message,       setMessage]         = useState("")
    const [messages,      setMessages]        = useState([])
    const [sources,       setSources]         = useState([])
    const [verification,  setVerification]    = useState(null)
    const [loading,       setLoading]         = useState(false)
    const [activeDocId,   setActiveDocId]     = useState(null)
    const [activeDocName, setActiveDocName]   = useState(null)
    const [selectedModel, setSelectedModel]   = useState("llama-3.3-70b-versatile")

    // Track which session the current messages belong to.
    // This lets us skip the history-reload useEffect when WE just created the session
    // (avoiding a race condition that would wipe in-flight messages).
    const currentSessionRef = useRef(null)

    // Only reload history when the user explicitly switches to a different session
    // (i.e., sessionId changes AND it's not the session we just created)
    useEffect(() => {
        if (!sessionId) {
            setMessages([])
            setSources([])
            setVerification(null)
            currentSessionRef.current = null
            return
        }

        // If this is the session we just created, DON'T reload (messages are already in state)
        if (currentSessionRef.current === sessionId) return

        // Different session selected from sidebar — load its history
        currentSessionRef.current = sessionId
        setMessages([])
        setSources([])
        setVerification(null)
        loadHistory(sessionId)
    }, [sessionId])

    async function loadHistory(sid) {
        try {
            const res  = await fetch(`${API}/history/messages/${sid}`, {
                headers: { Authorization: `Bearer ${token}` },
            })
            const data = await res.json()
            if (Array.isArray(data)) {
                setMessages(data.map(m => ({ role: m.role, content: m.content })))
            }
        } catch (err) {
            console.error("Failed to load history:", err)
        }
    }

    async function autoTitleSession(sid, firstMessage) {
        // Use the first 50 chars of the user's first message as the session title
        const title = firstMessage.trim().slice(0, 50)
        try {
            await fetch(`${API}/history/session/${sid}/title`, {
                method:  "PATCH",
                headers: {
                    "Content-Type":  "application/json",
                    "Authorization": `Bearer ${token}`,
                },
                body: JSON.stringify({ title }),
            })
            onTitleUpdated?.()
        } catch {
            // Non-critical — ignore failures
        }
    }

    function handleDocumentReady(docId, filename) {
        setActiveDocId(docId)
        setActiveDocName(filename)
    }

    async function sendMessage() {

        if (!message.trim()) return

        const userMsg = { role: "user", content: message }
        setMessages(prev => [...prev, userMsg])
        setMessage("")
        setLoading(true)
        setSources([])
        setVerification(null)

        let sid = sessionId
        const isNewSession = !sid

        // Auto-create session if needed
        if (!sid) {
            try {
                const res  = await fetch(`${API}/history/session`, {
                    method:  "POST",
                    headers: { Authorization: `Bearer ${token}` },
                })
                const data = await res.json()
                sid = data.session_id

                // Mark this session as "current" BEFORE calling onSessionCreated
                // so the useEffect doesn't trigger a history-reload over our messages
                currentSessionRef.current = sid
                onSessionCreated?.(sid)

                // Auto-title the session with the first message
                autoTitleSession(sid, userMsg.content)

            } catch (err) {
                console.error("Session creation failed:", err)
            }
        }

        try {
            const res = await fetch(`${API}/agents/stream`, {
                method:  "POST",
                headers: {
                    "Content-Type":  "application/json",
                    "Authorization": `Bearer ${token}`,
                },
                body: JSON.stringify({
                    query:       userMsg.content,
                    session_id:  sid,
                    document_id: activeDocId,
                    model:       selectedModel,
                }),
            })

            if (!res.ok) throw new Error(`HTTP ${res.status}`)

            // Prepare a placeholder for the incoming AI message
            const aiMsgIndex = messages.length + 1 // +1 for the user msg we just added
            setMessages(prev => [
                ...prev, 
                { role: "assistant", content: "", routing: null }
            ])

            const reader = res.body.getReader()
            const decoder = new TextDecoder()
            let buffer = ""

            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                
                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n\n')
                
                // Keep the last incomplete line in the buffer
                buffer = lines.pop() || ""

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        try {
                            const data = JSON.parse(line.slice(6))
                            
                            if (data.type === "chunk") {
                                setMessages(prev => {
                                    const next = [...prev]
                                    next[aiMsgIndex] = {
                                        ...next[aiMsgIndex],
                                        content: next[aiMsgIndex].content + data.value
                                    }
                                    return next
                                })
                            } else if (data.type === "routing") {
                                setMessages(prev => {
                                    const next = [...prev]
                                    next[aiMsgIndex] = {
                                        ...next[aiMsgIndex],
                                        routing: data.value
                                    }
                                    return next
                                })
                            } else if (data.type === "sources") {
                                setSources(data.value)
                            } else if (data.type === "verification") {
                                setVerification(data.value)
                            } else if (data.type === "error") {
                                throw new Error(data.value)
                            } else if (data.type === "done") {
                                // stream finished
                            }
                        } catch (e) {
                            console.error("Parse error on chunk:", e)
                        }
                    }
                }
            }

        } catch (err) {
            console.error(err)
            setMessages(prev => {
                // If it failed midway, append error to the streaming message
                const next = [...prev]
                const last = next[next.length - 1]
                if (last.role === "assistant") {
                    last.content += "\n\n❌ Error connecting to OpsPilot AI backend."
                } else {
                    next.push({ role: "assistant", content: "❌ Error connecting to OpsPilot AI backend." })
                }
                return next
            })
        } finally {
            setLoading(false)
        }
    }

    function handleKeyDown(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") sendMessage()
    }

    return (
        <div className="flex flex-col min-h-screen bg-transparent text-gray-200">

            {/* ── Header ── */}
            <div className="border-b border-white/10 px-6 py-4 flex items-center justify-between bg-white/5 backdrop-blur-md shadow-sm z-10">

                <div>
                    <h2 className="text-lg font-semibold text-white tracking-wide drop-shadow-md">
                        {activeDocName ? `📄 ${activeDocName}` : "OpsPilot AI Chat"}
                    </h2>
                    <p className="text-xs text-gray-500">
                        {activeDocId ? `Scoped to: ${activeDocId}` : "Searching all documents"}
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="bg-[#1F2937] text-xs text-gray-300 border border-gray-700 rounded-lg px-3 py-1.5 outline-none focus:border-blue-500 transition-colors"
                    >
                        <option value="llama-3.3-70b-versatile">Llama 3.3 70B (Recommended)</option>
                        <option value="llama-3.1-8b-instant">Llama 3.1 8B (Fast)</option>
                        <option value="mixtral-8x7b-32768">Mixtral 8x7B (Long Context)</option>
                    </select>

                    {activeDocId && (
                        <button
                            onClick={() => { setActiveDocId(null); setActiveDocName(null) }}
                            className="text-xs text-gray-500 hover:text-red-400 transition border border-gray-700 px-3 py-1 rounded-lg"
                        >
                            ✕ Clear scope
                        </button>
                    )}
                </div>

            </div>

            {/* ── Conversation History ── */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">

                {messages.length === 0 && !loading && (
                    <div className="flex flex-col items-center justify-center h-full py-20 text-center">
                        <div className="text-5xl mb-4">🤖</div>
                        <h3 className="text-xl font-semibold text-gray-300 mb-2">
                            Ask OpsPilot AI anything
                        </h3>
                        <p className="text-gray-500 text-sm max-w-sm">
                            Upload a PDF to query your documents, or ask general AI engineering questions.
                            The AI will automatically decide how to best answer.
                        </p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"} animate-fade-in-up`}
                        style={{ animationDelay: `${idx * 0.05}s` }}
                    >
                        <div className={`
                            max-w-2xl px-5 py-4 rounded-2xl text-sm leading-relaxed shadow-lg overflow-hidden
                            ${msg.role === "user"
                                ? "bg-gradient-to-br from-blue-600 to-indigo-600 text-white rounded-br-sm shadow-[0_0_15px_rgba(59,130,246,0.3)] border border-blue-400/20"
                                : "bg-white/10 backdrop-blur-md text-gray-200 rounded-bl-sm border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]"
                            }
                        `}>
                            {msg.role === "assistant"
                                ? <div className="prose prose-invert prose-sm max-w-none break-words overflow-hidden">
                                    <ReactMarkdown
                                        components={{
                                            code({node, inline, className, children, ...props}) {
                                                const match = /language-(\w+)/.exec(className || '')
                                                return !inline && match ? (
                                                    <SyntaxHighlighter
                                                        {...props}
                                                        children={String(children).replace(/\n$/, '')}
                                                        style={atomDark}
                                                        language={match[1]}
                                                        PreTag="div"
                                                        className="rounded-xl overflow-hidden my-2"
                                                    />
                                                ) : (
                                                    <code {...props} className={`${className} bg-gray-800 text-blue-300 px-1 py-0.5 rounded text-[0.9em]`}>
                                                        {children}
                                                    </code>
                                                )
                                            }
                                        }}
                                    >
                                        {msg.content}
                                    </ReactMarkdown>
                                  </div>
                                : msg.content
                            }
                        </div>

                        {/* Routing badge — shows which LangGraph path the planner chose */}
                        {msg.role === "assistant" && msg.routing && (
                            <div className="mt-1 flex items-center gap-1">
                                <span className={`
                                    text-xs px-2 py-0.5 rounded-full
                                    ${msg.routing === "rag"   ? "bg-blue-900/40 text-blue-400 border border-blue-800/40" : ""}
                                    ${msg.routing === "chat"  ? "bg-green-900/40 text-green-400 border border-green-800/40" : ""}
                                    ${msg.routing === "tools" ? "bg-orange-900/40 text-orange-400 border border-orange-800/40" : ""}
                                `}>
                                    {msg.routing === "rag"   && "📄 RAG"}
                                    {msg.routing === "chat"  && "💬 Chat"}
                                    {msg.routing === "tools" && "🔧 Tools"}
                                </span>
                            </div>
                        )}
                    </div>
                ))}

                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-[#1F2937] border border-gray-700 px-4 py-3 rounded-2xl rounded-bl-sm">
                            <span className="flex gap-1">
                                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" />
                            </span>
                        </div>
                    </div>
                )}

            </div>

            {/* ── Sources & Verification ── */}
            {(sources.length > 0 || verification) && (
                <div className="px-6 py-3 space-y-3 border-t border-gray-800 max-h-64 overflow-y-auto">

                    {sources.length > 0 && (
                        <div>
                            <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wider">
                                📚 Sources ({sources.length})
                            </p>
                            <div className="flex gap-2 flex-wrap">
                                {sources.map(src => (
                                    <div
                                        key={src.id}
                                        className="
                                            bg-[#1F2937] border border-gray-700
                                            rounded-xl px-3 py-2 text-xs max-w-xs
                                        "
                                    >
                                        <span className="text-blue-400 font-bold">[{src.id}]</span>{" "}
                                        <span className="text-gray-300">{src.source}</span>{" "}
                                        <span className="text-gray-500">p.{src.page}</span>
                                        {src.relevance_score != null && (
                                            <span className="text-gray-600 ml-1">({src.relevance_score})</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {verification && (
                        <div className="text-xs">
                            <span className={`font-medium ${verification.verified ? "text-green-400" : "text-yellow-400"}`}>
                                {verification.verified ? "✅ Verified" : "⚠️ Partially verified"}
                            </span>
                            {verification.issues?.filter(i => i.missing).map((iss, i) => (
                                <div key={i} className="text-gray-500 mt-1">⚠️ Unverified: {iss.claim}</div>
                            ))}
                        </div>
                    )}

                </div>
            )}

            {/* ── Input Area ── */}
            <div className="border-t border-white/10 p-4 space-y-3 bg-white/5 backdrop-blur-md z-10">

                <FileUpload onDocumentReady={handleDocumentReady} />

                <div className="bg-black/20 backdrop-blur-xl border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-2xl p-3 flex gap-3 items-end transition-all focus-within:border-blue-500/50 focus-within:bg-black/30">

                    <textarea
                        className="
                            flex-1 bg-transparent outline-none resize-none
                            text-white placeholder-gray-500 text-sm leading-relaxed
                            max-h-40
                        "
                        rows="2"
                        placeholder="Ask about your document, or anything else…  (Ctrl+Enter to send)"
                        value={message}
                        onChange={e => setMessage(e.target.value)}
                        onKeyDown={handleKeyDown}
                    />

                    <button
                        onClick={sendMessage}
                        disabled={loading || !message.trim()}
                        className="
                            bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500
                            disabled:from-gray-700 disabled:to-gray-800 disabled:text-gray-500 disabled:cursor-not-allowed
                            text-white px-5 py-2.5 rounded-xl text-sm font-medium
                            transition-all duration-300 shrink-0 shadow-lg hover:shadow-[0_0_15px_rgba(79,70,229,0.5)]
                            disabled:shadow-none
                        "
                    >
                        {loading ? "…" : "Send"}
                    </button>

                </div>

            </div>

        </div>
    )
}
