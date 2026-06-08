import { useState } from "react"

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

function FileUpload({ onDocumentReady }) {

    const [file, setFile]           = useState(null)
    const [status, setStatus]       = useState("")
    const [processing, setProcessing] = useState(false)
    const [success, setSuccess]     = useState(false)

    function wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms))
    }

    async function pollTask(taskId) {

        for (let attempt = 0; attempt < 60; attempt += 1) {

            const res  = await fetch(`${API}/rag/task/${taskId}`)
            const data = await res.json()

            if (data.status === "SUCCESS") {
                const chunks = data.result?.chunks_created ?? 0
                setStatus(`✅ Indexed ${chunks} chunks — ready to answer questions.`)
                setSuccess(true)
                return
            }

            if (data.status === "FAILURE") {
                setStatus(`❌ ${data.result?.error || "PDF indexing failed. Check backend worker logs."}`)
                return
            }

            // Show a progress pulse
            const dots = ".".repeat((attempt % 3) + 1)
            setStatus(`Indexing PDF${dots}  (attempt ${attempt + 1}/60)`)

            await wait(2000)
        }

        setStatus("⚠️ Indexing is taking longer than expected. Please check backend logs.")
    }

    async function uploadFile() {

        if (!file || processing) return

        setProcessing(true)
        setSuccess(false)

        const formData = new FormData()
        formData.append("file", file)

        setStatus("Uploading PDF…")

        try {
            const res  = await fetch(`${API}/rag/upload`, {
                method: "POST",
                body:   formData,
            })
            const data = await res.json()

            if (!res.ok) {
                setStatus(`❌ ${data.detail || "Upload failed."}`)
                return
            }

            setStatus(`Upload successful. Processing task: ${data.task_id}`)

            // Tell parent which document_id was indexed so queries can be scoped
            if (data.document_id && onDocumentReady) {
                onDocumentReady(data.document_id, data.filename)
            }

            await pollTask(data.task_id)

        } catch (error) {
            console.error(error)
            setStatus("❌ Upload failed. Is the backend running?")
        } finally {
            setProcessing(false)
        }
    }

    return (
        <div className="bg-[#111827] px-4 py-3 rounded-xl shadow-md mb-4 border border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
                <span className="text-lg">📄</span>
                <label className="
                    cursor-pointer
                    bg-[#1F2937]
                    border border-gray-600
                    hover:border-blue-500
                    text-gray-300
                    px-3 py-1.5
                    rounded-lg
                    text-sm
                    transition
                ">
                    {file ? file.name : "Choose PDF"}
                    <input
                        type="file"
                        accept=".pdf"
                        className="hidden"
                        onChange={(e) => {
                            setFile(e.target.files[0])
                            setStatus("")
                            setSuccess(false)
                        }}
                    />
                </label>

                <button
                    onClick={uploadFile}
                    disabled={!file || processing}
                    className="
                        bg-blue-600
                        hover:bg-blue-700
                        disabled:bg-gray-700
                        disabled:cursor-not-allowed
                        px-4 py-1.5
                        rounded-lg
                        text-sm
                        font-medium
                        transition
                    "
                >
                    {processing ? "Processing…" : "Upload"}
                </button>
            </div>

            {status && (
                <div className={`text-xs ${success ? "text-green-400" : "text-gray-400"}`}>
                    {status}
                </div>
            )}
        </div>
    )
}

export default FileUpload
