import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

const DEBOUNCE_MS = 300

// Searches GET /market/search once the user pauses typing (not on every keystroke)
export function useStockSearch(query) {
  const [state, setState] = useState({ query: '', results: [], error: '' })
  const trimmed = query.trim()

  useEffect(() => {
    if (!trimmed) {
      return
    }
    let cancelled = false
    const timer = setTimeout(() => {
      apiFetch(`/market/search?q=${encodeURIComponent(trimmed)}&limit=8`)
        .then((results) => !cancelled && setState({ query: trimmed, results, error: '' }))
        .catch((err) => !cancelled && setState({ query: trimmed, results: [], error: err.message }))
    }, DEBOUNCE_MS)
    // Typing again before the timer fires cancels this search; a late reply for an old query is ignored
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [trimmed])

  if (!trimmed) {
    return { results: [], error: '', searching: false }
  }
  return { results: state.results, error: state.error, searching: state.query !== trimmed }
}