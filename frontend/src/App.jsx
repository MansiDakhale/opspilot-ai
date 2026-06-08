import { useState } from "react"
import { AuthProvider, useAuth } from "./context/AuthContext"
import LoginPage   from "./pages/LoginPage"
import SignupPage  from "./pages/SignupPage"
import ChatPage    from "./pages/ChatPage"
import Sidebar     from "./components/Sidebar"

function AppShell() {

    const { isAuthenticated } = useAuth()
    const [showSignup,        setShowSignup]        = useState(false)
    const [activeSessionId,   setActiveSessionId]   = useState(null)
    const [refreshSidebar,    setRefreshSidebar]    = useState(0)

    // Not logged in → show auth screens
    if (!isAuthenticated) {
        return showSignup
            ? <SignupPage  onSwitchToLogin={() => setShowSignup(false)} />
            : <LoginPage   onSwitchToSignup={() => setShowSignup(true)} />
    }

    // Logged in → full platform layout
    return (
        <div className="flex min-h-screen bg-[#050A15] relative overflow-hidden text-gray-200">
            
            {/* Ambient glowing background orbs */}
            <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-900/30 rounded-full blur-[120px] pointer-events-none animate-pulse-slow" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-indigo-900/20 rounded-full blur-[120px] pointer-events-none animate-pulse-slow" style={{animationDelay: "2s"}} />

            <div className="relative z-10 flex w-full h-screen">
                <Sidebar
                    activeSessionId={activeSessionId}
                    onSelectSession={setActiveSessionId}
                    onNewChat={setActiveSessionId}
                    refreshTrigger={refreshSidebar}
                />

                <main className="flex-1 overflow-hidden flex flex-col">
                    <ChatPage
                        sessionId={activeSessionId}
                        onSessionCreated={setActiveSessionId}
                        onTitleUpdated={() => setRefreshSidebar(prev => prev + 1)}
                    />
                </main>
            </div>

        </div>
    )
}

export default function App() {
    return (
        <AuthProvider>
            <AppShell />
        </AuthProvider>
    )
}