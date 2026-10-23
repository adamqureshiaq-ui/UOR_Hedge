import { NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import RequireAuth from './auth/RequireAuth.jsx'
import { useAuth } from './auth/useAuth.js'
import BackendStatus from './components/BackendStatus.jsx'
import LoginPage from './pages/LoginPage.jsx'
import PlaceholderPage from './pages/PlaceholderPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'

const PAGES = [
  { path: '/', title: 'Dashboard' },
  { path: '/trade', title: 'Trade' },
  { path: '/leaderboard', title: 'Leaderboard' },
  { path: '/analytics', title: 'Analytics' },
]

export default function App() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="app">
      <header className="app-header">
        <span className="brand">UOR Hedge</span>
        <nav>
          {user ? (
            PAGES.map((page) => (
              <NavLink key={page.path} to={page.path} end>
                {page.title}
              </NavLink>
            ))
          ) : (
            <>
              <NavLink to="/login">Log in</NavLink>
              <NavLink to="/register">Register</NavLink>
            </>
          )}
        </nav>
        <BackendStatus />
        {user && (
          <div className="user-menu">
            <span className="muted">{user.username}</span>
            <button type="button" className="link-button" onClick={handleLogout}>
              Log out
            </button>
          </div>
        )}
      </header>

      <main>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<RequireAuth />}>
            {PAGES.map((page) => (
              <Route key={page.path} path={page.path} element={<PlaceholderPage title={page.title} />} />
            ))}
          </Route>
          <Route path="*" element={<PlaceholderPage title="Page not found" />} />
        </Routes>
      </main>
    </div>
  )
}