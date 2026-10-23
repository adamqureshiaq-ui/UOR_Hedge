import { createContext } from 'react'

// Shared "who is logged in" state. AuthProvider.jsx fills it in; useAuth.js lets any component read it.
export const AuthContext = createContext(null)