import { useState } from "react"

function FileUpload() {

    const [file, setFile] = useState(null)

    const [status, setStatus] = useState("")

    async function uploadFile() {

        if (!file) return

        const formData = new FormData()

        formData.append("file", file)

        setStatus("Uploading PDF...")

        const res = await fetch(
            "http://localhost:8000/rag/upload",
            {
                method: "POST",
                body: formData
            }
        )

        const data = await res.json()

        setStatus(
            `Processing started | Task ID: ${data.task_id}`
        )
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
                className="
                    bg-blue-600
                    hover:bg-blue-700
                    px-5
                    py-2
                    rounded-xl
                "
            >
                Upload PDF
            </button>

            <div className="mt-4 text-gray-400">
                {status}
            </div>

        </div>
    )
}

export default FileUpload