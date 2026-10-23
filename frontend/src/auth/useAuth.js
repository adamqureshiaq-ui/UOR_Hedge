import { useContext } from 'react'
import { AuthContext } from './AuthContext.js'

// Any component can call useAuth() to get { user, checking, login, register, logout }
export function useAuth() {
  const auth = useContext(AuthContext)
  if (!auth) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return auth
}