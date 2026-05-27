import { useState } from "react"

function FileUpload() {

    const [file, setFile] = useState(null)

    const [status, setStatus] = useState("")

    const [processing, setProcessing] = useState(false)

    function wait(ms) {

        return new Promise(resolve => setTimeout(resolve, ms))
    }

    async function pollTask(taskId) {

        for (let attempt = 0; attempt < 60; attempt += 1) {

            const res = await fetch(
                `http://localhost:8000/rag/task/${taskId}`
            )

            const data = await res.json()

            if (data.status === "SUCCESS") {

                setStatus(
                    `Indexed ${data.result?.chunks_created ?? 0} chunks. You can ask questions now.`
                )

                return
            }

            if (data.status === "FAILURE") {

                setStatus("PDF indexing failed. Check backend worker logs.")

                return
            }

            setStatus(`Indexing PDF... Status: ${data.status}`)

            await wait(2000)
        }

        setStatus("Indexing is still running. Please check again in a moment.")
    }

    async function uploadFile() {

        if (!file || processing) return

        setProcessing(true)

        const formData = new FormData()

        formData.append("file", file)

        setStatus("Uploading PDF...")

        try {

            const res = await fetch(
                "http://localhost:8000/rag/upload",
                {
                    method: "POST",
                    body: formData
                }
            )

            const data = await res.json()

            if (!res.ok) {

                setStatus(data.detail || "Upload failed.")

                return
            }

            setStatus(`Processing started | Task ID: ${data.task_id}`)

            await pollTask(data.task_id)

        } catch (error) {

            console.error(error)

            setStatus("Upload failed. Check that the backend is running.")

        } finally {

            setProcessing(false)
        }
    }

    return (

        <div className="
            bg-[#111827]
            p-6
            rounded-2xl
            shadow-xl
            mb-6
        ">

            <h2 className="text-xl font-semibold mb-4">
                Upload Documents
            </h2>

            <input
                type="file"
                accept=".pdf"
                onChange={(e) =>
                    setFile(e.target.files[0])
                }
                className="mb-4"
            />

            <button
                onClick={uploadFile}
                disabled={processing}
                className="
                    bg-blue-600
                    hover:bg-blue-700
                    disabled:bg-gray-600
                    disabled:cursor-not-allowed
                    px-5
                    py-2
                    rounded-xl
                "
            >
                {processing ? "Processing..." : "Upload PDF"}
            </button>

            <div className="mt-4 text-gray-400">
                {status}
            </div>

        </div>
    )
}

export default FileUpload
