import { useCallback, useEffect, useMemo, useState } from 'react'
import { AUTH_EXPIRED_EVENT, apiFetch, clearToken, getToken, saveToken } from '../api.js'
import { AuthContext } from './AuthContext.js'

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // If a token was saved earlier, we don't know who is logged in until /me answers
  const [checking, setChecking] = useState(() => Boolean(getToken()))

  // On page load, turn a saved token back into a logged-in user
  useEffect(() => {
    if (!getToken()) {
      return
    }
    apiFetch('/me')
      .then(setUser)
      .catch(() => setUser(null)) // apiFetch already clears the token if it was rejected
      .finally(() => setChecking(false))
  }, [])

  // Any request that comes back 401 means the token has expired: log the user out
  useEffect(() => {
    const handleExpired = () => setUser(null)
    window.addEventListener(AUTH_EXPIRED_EVENT, handleExpired)
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleExpired)
  }, [])

  const login = useCallback(async (username, password) => {
    const { access_token } = await apiFetch('/login', { method: 'POST', form: { username, password } })
    saveToken(access_token)
    setUser(await apiFetch('/me'))
  }, [])

  const register = useCallback(
    async ({ username, email, password }) => {
      await apiFetch('/register', { method: 'POST', body: { username, email, password } })
      await login(username, password) // log straight in after creating the account
    },
    [login],
  )

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, checking, login, register, logout }),
    [user, checking, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}