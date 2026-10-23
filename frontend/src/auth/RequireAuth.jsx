import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './useAuth.js'

// Wraps every members-only page: logged-out visitors are sent to /login,
// and come back to the page they wanted after logging in
export default function RequireAuth() {
  const { user, checking } = useAuth()
  const location = useLocation()

  if (checking) {
    return <p className="muted">Loading…</p>
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}