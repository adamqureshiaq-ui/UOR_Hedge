import { NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import RequireAuth from './auth/RequireAuth.jsx'
import { useAuth } from './auth/useAuth.js'
import BackendStatus from './components/BackendStatus.jsx'
import LoginPage from './pages/LoginPage.jsx'
import PlaceholderPage from './pages/PlaceholderPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import TradePage from './pages/TradePage.jsx'
import LeaderboardPage from './pages/LeaderboardPage.jsx'

const PAGES = [
  { path: '/', title: 'Dashboard', element: <DashboardPage /> },
  { path: '/trade', title: 'Trade', element: <TradePage /> },
  { path: '/leaderboard', title: 'Leaderboard', element: <LeaderboardPage /> },
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
              <Route key={page.path} 
              path={page.path} 
              element={page.element ?? <PlaceholderPage title={page.title} />} />
            ))}
          </Route>
          <Route path="*" element={<PlaceholderPage title="Page not found" />} />
        </Routes>
      </main>
    </div>
  )
}