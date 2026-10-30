import { useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

const REFRESH_INTERVAL_MS = 60_000

// Loads GET /leaderboard (every member), then quietly refreshes it every minute while the tab is visible
export function useLeaderboard() {
  const [leaderboard, setLeaderboard] = useState(null)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [updatedAt, setUpdatedAt] = useState(null)

  // limit=500 is the backend's maximum: enough to find every member's own row in a society-sized group
  const load = useCallback(
    () =>
      apiFetch('/leaderboard?limit=500')
        .then((data) => {
          setLeaderboard(data)
          setUpdatedAt(new Date())
          setError('')
        })
        .catch((err) => setError(err.message)),
    [],
  )

  const refresh = useCallback(async () => {
    setRefreshing(true)
    await load()
    setRefreshing(false)
  }, [load])

  useEffect(() => {
    load()
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') {
        load()
      }
    }, REFRESH_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [load])

  return { leaderboard, error, refreshing, updatedAt, refresh }
}