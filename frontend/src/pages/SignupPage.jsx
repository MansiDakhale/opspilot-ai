import { useState } from "react"
import { useAuth } from "../context/AuthContext"

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

export default function SignupPage({ onSwitchToLogin }) {

    const { login }             = useAuth()
    const [fullName,  setFullName]  = useState("")
    const [email,     setEmail]     = useState("")
    const [password,  setPassword]  = useState("")
    const [error,     setError]     = useState("")
    const [loading,   setLoading]   = useState(false)

    async function handleSubmit(e) {
        e.preventDefault()
        setError("")
        setLoading(true)

        try {
            // Step 1: Register
            const signupRes  = await fetch(`${API}/auth/signup`, {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify({ email, password, full_name: fullName }),
            })
            const signupData = await signupRes.json()

            if (!signupRes.ok) {
                setError(signupData.detail || "Signup failed.")
                return
            }

            // Step 2: Auto-login after signup
            const loginRes  = await fetch(`${API}/auth/login`, {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify({ email, password }),
            })
            const loginData = await loginRes.json()

            if (loginRes.ok) {
                login(loginData.access_token, { email, full_name: fullName })
            } else {
                // Redirect to login if auto-login fails
                onSwitchToLogin()
            }

        } catch {
            setError("Cannot connect to the backend.")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-[#0B1120] flex items-center justify-center px-4">

            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -right-40 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl" />
                <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl" />
            </div>

            <div className="relative w-full max-w-md">

                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-white tracking-tight">
                        Ops<span className="text-blue-400">Pilot</span> AI
                    </h1>
                    <p className="text-gray-400 mt-2 text-sm">Production-grade Agentic AI Platform</p>
                </div>

                <div className="bg-[#111827]/80 backdrop-blur border border-gray-800 rounded-2xl p-8 shadow-2xl">

                    <h2 className="text-xl font-semibold text-white mb-6">Create Account</h2>

                    <form onSubmit={handleSubmit} className="space-y-4">

                        <div>
                            <label className="block text-sm text-gray-400 mb-1">Full Name</label>
                            <input
                                id="signup-name"
                                type="text"
                                required
                                value={fullName}
                                onChange={e => setFullName(e.target.value)}
                                placeholder="John Doe"
                                className="
                                    w-full bg-[#1F2937] border border-gray-700
                                    focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                                    rounded-xl px-4 py-3 text-white placeholder-gray-500
                                    outline-none transition text-sm
                                "
                            />
                        </div>

                        <div>
                            <label className="block text-sm text-gray-400 mb-1">Email</label>
                            <input
                                id="signup-email"
                                type="email"
                                required
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="you@example.com"
                                className="
                                    w-full bg-[#1F2937] border border-gray-700
                                    focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                                    rounded-xl px-4 py-3 text-white placeholder-gray-500
                                    outline-none transition text-sm
                                "
                            />
                        </div>

                        <div>
                            <label className="block text-sm text-gray-400 mb-1">Password</label>
                            <input
                                id="signup-password"
                                type="password"
                                required
                                minLength={6}
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="••••••••"
                                className="
                                    w-full bg-[#1F2937] border border-gray-700
                                    focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                                    rounded-xl px-4 py-3 text-white placeholder-gray-500
                                    outline-none transition text-sm
                                "
                            />
                        </div>

                        {error && (
                            <div className="text-red-400 text-sm bg-red-900/20 border border-red-800/40 rounded-xl px-4 py-2">
                                {error}
                            </div>
                        )}

                        <button
                            id="signup-submit"
                            type="submit"
                            disabled={loading}
                            className="
                                w-full bg-blue-600 hover:bg-blue-700
                                disabled:bg-gray-700 disabled:cursor-not-allowed
                                text-white font-semibold rounded-xl py-3
                                transition text-sm mt-2
                            "
                        >
                            {loading ? "Creating account…" : "Create Account"}
                        </button>

                    </form>

                    <p className="text-center text-sm text-gray-500 mt-6">
                        Already have an account?{" "}
                        <button
                            onClick={onSwitchToLogin}
                            className="text-blue-400 hover:text-blue-300 transition"
                        >
                            Sign in
                        </button>
                    </p>

                </div>

            </div>
        </div>
    )
}
