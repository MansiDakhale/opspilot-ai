import { useState } from "react"
import ReactMarkdown from "react-markdown"
import FileUpload from "../components/FileUpload"

function ChatPage() {

    const [message, setMessage] = useState("")
    const [response, setResponse] = useState("")
    const [sources, setSources] = useState([])
    const [verification, setVerification] = useState(null)
    const [sessionId, setSessionId] = useState(null)
    const [loading, setLoading] = useState(false)

    async function createSession() {

        try {

            const res = await fetch(
                "http://localhost:8000/history/session",
                {
                    method: "POST"
                }
            )

            const data = await res.json()

            setSessionId(data.session_id)

            return data.session_id

        } catch (error) {

            console.error(error)

            return null
        }
    }

    async function sendMessage() {

        if (!message.trim()) return

        setLoading(true)

        setResponse("")

        setSources([])

        setVerification(null)
        
        try {

            let activeSessionId = sessionId

            if (!activeSessionId) {

                activeSessionId = await createSession()
            }

            const res = await fetch(
                "http://localhost:8000/rag/query/verify",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        query: message,
                        session_id: activeSessionId
                    })
                }
            )

            const data = await res.json()

            if (data.response) setResponse(data.response)

            setSources(data.sources || [])

            setVerification(data.verification || null)

        } catch (error) {

            console.error(error)

            setResponse(
                "Error retrieving response."
            )
        } finally {

            setLoading(false)
        }
    }

    return (

        <div className="min-h-screen bg-[#0B1120] text-white flex flex-col">

            {/* Header */}

            <div className="border-b border-gray-800 p-4">

                <h1 className="text-3xl font-bold">
                    OpsPilot AI
                </h1>

                <p className="text-gray-400 mt-1">
                    Production-grade Agentic AI Platform
                </p>

            </div>

            {/* Main */}

            <div className="flex-1 flex justify-center p-6">

                <div className="w-full max-w-4xl">

                    {/* File Upload */}

                    <FileUpload />

                    {/* Input Box */}

                    <div className="bg-[#111827] rounded-2xl p-4 shadow-xl">

                        <textarea
                            className="
                                w-full
                                bg-transparent
                                outline-none
                                resize-none
                                text-white
                                placeholder-gray-500
                            "
                            rows="4"
                            placeholder="Ask OpsPilot AI..."
                            value={message}
                            onChange={(e) =>
                                setMessage(e.target.value)
                            }
                        />

                        <div className="flex justify-end mt-4">

                            <button
                                className="
                                    bg-blue-600
                                    hover:bg-blue-700
                                    px-6
                                    py-2
                                    rounded-xl
                                    font-medium
                                    transition
                                "
                                onClick={sendMessage}
                            >
                                Send
                            </button>

                        </div>

                    </div>

                    {/* Response */}

                    <div className="
                        mt-6
                        bg-[#111827]
                        rounded-2xl
                        p-6
                        shadow-xl
                        min-h-[300px]
                    ">

                        {loading && (

                            <div className="text-blue-400 mb-4">

                                OpsPilot AI is thinking...

                            </div>
                        )}

                        <div className="
                            prose
                            prose-invert
                            max-w-none
                        ">

                            <ReactMarkdown>
                                {response}
                            </ReactMarkdown>

                        </div>

                        {/* Sources */}

                        {
                            sources.length > 0 && (

                                <div className="mt-8">

                                    <h2 className="
                                        text-xl
                                        font-semibold
                                        mb-4
                                        text-white
                                    ">
                                        Sources
                                    </h2>

                                    <div className="space-y-4">

                                        {
                                            sources.map((source, index) => (

                                                <div
                                                    key={index}
                                                    className="
                                                        bg-[#1F2937]
                                                        p-4
                                                        rounded-xl
                                                        border
                                                        border-gray-700
                                                    "
                                                >

                                                    <div className="
                                                        text-blue-400
                                                        font-semibold
                                                        mb-2
                                                    ">

                                                        [#{source.id}] {source.source} | Page: {source.page}

                                                    </div>

                                                    <div className="
                                                        text-gray-300
                                                        text-sm
                                                        leading-relaxed
                                                    ">

                                                        {source.content}

                                                    </div>

                                                </div>
                                            ))
                                        }

                                    </div>

                                </div>
                            )
                        }

                        {/* Verification */}

                        {
                            verification && (

                                <div className="mt-8">

                                    <h2 className="text-xl font-semibold mb-4 text-white">Verification</h2>

                                    <div className="bg-[#1F2937] p-4 rounded-xl border border-gray-700">

                                        <div className="text-gray-300 mb-2">Verified: {verification.verified ? 'Yes' : 'No'}</div>

                                        {
                                            verification.issues && verification.issues.length > 0 && (

                                                <div className="text-sm text-gray-300">

                                                    <div className="font-semibold mb-2">Issues:</div>

                                                    <ul className="list-disc pl-5">

                                                        {verification.issues.map((iss, i) => (

                                                            <li key={i} className="mb-2">

                                                                <div className="font-medium">{iss.claim}</div>

                                                                <div className="text-xs text-gray-400">Supporting sources: {iss.supporting_sources && iss.supporting_sources.length > 0 ? iss.supporting_sources.join(', ') : 'None'}</div>

                                                            </li>

                                                        ))}

                                                    </ul>

                                                </div>

                                            )

                                        }

                                    </div>

                                </div>

                            )
                        }

                    </div>

                </div>

            </div>

        </div>
    )
}

export default ChatPage
