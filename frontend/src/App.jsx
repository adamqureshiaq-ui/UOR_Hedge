import { NavLink, Route, Routes } from 'react-router-dom'
import BackendStatus from './components/BackendStatus.jsx'
import PlaceholderPage from './pages/PlaceholderPage.jsx'

const PAGES = [
  { path: '/', title: 'Dashboard' },
  { path: '/trade', title: 'Trade' },
  { path: '/leaderboard', title: 'Leaderboard' },
  { path: '/analytics', title: 'Analytics' },
]

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <span className="brand">UOR Hedge</span>
        <nav>
          {PAGES.map((page) => (
            <NavLink key={page.path} to={page.path} end>
              {page.title}
            </NavLink>
          ))}
          <NavLink to="/login">Log in</NavLink>
        </nav>
        <BackendStatus />
      </header>

      <main>
        <Routes>
          {PAGES.map((page) => (
            <Route key={page.path} path={page.path} element={<PlaceholderPage title={page.title} />} />
          ))}
          <Route path="/login" element={<PlaceholderPage title="Log in" />} />
          <Route path="/register" element={<PlaceholderPage title="Register" />} />
          <Route path="*" element={<PlaceholderPage title="Page not found" />} />
        </Routes>
      </main>
    </div>
  )
}