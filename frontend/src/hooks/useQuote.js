import { useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

// Loads GET /market/quote/{symbol} whenever the symbol changes, or when reload() is called
export function useQuote(symbol) {
  const [state, setState] = useState({ symbol: null, quote: null, error: '', updatedAt: null })
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    if (!symbol) {
      return
    }
    let cancelled = false
    apiFetch(`/market/quote/${encodeURIComponent(symbol)}`)
      .then((quote) => !cancelled && setState({ symbol, quote, error: '', updatedAt: new Date() }))
      .catch((err) => !cancelled && setState({ symbol, quote: null, error: err.message, updatedAt: null }))
    return () => {
      cancelled = true // ignore a slow reply for a stock the user has already moved away from
    }
  }, [symbol, reloadCount])

  const reload = useCallback(() => setReloadCount((count) => count + 1), [])

  const current = symbol !== null && state.symbol === symbol
  return {
    quote: current ? state.quote : null,
    error: current ? state.error : '',
    loading: symbol !== null && !current,
    updatedAt: current ? state.updatedAt : null,
    reload,
  }
}