import { useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

const REFRESH_INTERVAL_MS = 30_000

// Loads GET /portfolio, then quietly refreshes it every 30 seconds while the tab is visible
export function usePortfolio() {
  const [portfolio, setPortfolio] = useState(null)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [updatedAt, setUpdatedAt] = useState(null)

  // State only changes once the request has finished (inside .then / .catch)
  const load = useCallback(
    () =>
      apiFetch('/portfolio')
        .then((data) => {
          setPortfolio(data)
          setUpdatedAt(new Date())
          setError('')
        })
        .catch((err) => setError(err.message)), // keep showing the last good numbers alongside the error
    [],
  )

  // The Refresh button: same request, but shows that it's working
  const refresh = useCallback(async () => {
    setRefreshing(true)
    await load()
    setRefreshing(false)
  }, [load])

  useEffect(() => {
    load()
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') {
        load() // skip refreshes while the tab is in the background
      }
    }, REFRESH_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [load])

  return { portfolio, error, refreshing, updatedAt, refresh }
}