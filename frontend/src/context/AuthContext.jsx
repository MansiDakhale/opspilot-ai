/**
 * AuthContext.jsx
 * 
 * Global authentication state. Stores the JWT token and current user
 * in localStorage so sessions persist across page refreshes.
 * 
 * Usage:
 *   const { token, user, login, logout } = useAuth()
 */

import { createContext, useContext, useState, useEffect } from "react"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {

    const [token, setToken] = useState(() => localStorage.getItem("opspilot_token"))
    const [user,  setUser]  = useState(() => {
        const stored = localStorage.getItem("opspilot_user")
        return stored ? JSON.parse(stored) : null
    })

    function login(accessToken, userInfo) {
        setToken(accessToken)
        setUser(userInfo)
        localStorage.setItem("opspilot_token", accessToken)
        localStorage.setItem("opspilot_user",  JSON.stringify(userInfo))
    }

    function logout() {
        setToken(null)
        setUser(null)
        localStorage.removeItem("opspilot_token")
        localStorage.removeItem("opspilot_user")
    }

    return (
        <AuthContext.Provider value={{ token, user, login, logout, isAuthenticated: !!token }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const ctx = useContext(AuthContext)
    if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>")
    return ctx
}
