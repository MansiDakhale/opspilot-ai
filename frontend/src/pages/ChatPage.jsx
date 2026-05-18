import { useState } from "react"
import ReactMarkdown from "react-markdown"
import FileUpload from "../components/FileUpload"

function ChatPage() {

    const [message, setMessage] = useState("")
    const [response, setResponse] = useState("")
    const [sources, setSources] = useState([])
    const [loading, setLoading] = useState(false)

    async function sendMessage() {

        if (!message.trim()) return

        setLoading(true)

        setResponse("")

        setSources([])
        
        try {

            const res = await fetch(
                "http://localhost:8000/rag/stream",
                {
                    method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    query: message
                })
            }
        )

        const reader = res.body.getReader()

        const decoder = new TextDecoder()

        while (true) {

            const { done, value } =
                await reader.read()

            if (done) {

                await fetchSources()

                break
            } 

            const chunk =
                decoder.decode(value)

            setResponse(prev => prev + chunk)
        }

    } catch (error) {

        console.error(error)

        setResponse(
            "Error retrieving response."
        )
    } finally {

            setLoading(false)
        }
    }

    async function fetchSources() {

        try {

            const res = await fetch(
                "http://localhost:8000/rag/query",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        query: message
                    })
                }
            )

            const data = await res.json()

            setSources(data.sources || [])

        } catch (error) {

            console.error(error)
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

                                                        {source.source}
                                                        {" "} | Page: {source.page}

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

                    </div>

                </div>

            </div>

        </div>
    )
}

export default ChatPage