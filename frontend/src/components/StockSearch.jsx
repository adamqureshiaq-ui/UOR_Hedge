import { useState } from 'react'
import { useStockSearch } from '../hooks/useStockSearch.js'

// Search box + results list. Calls onSelect(symbol) when a stock is picked.
export default function StockSearch({ selectedSymbol, onSelect }) {
  const [query, setQuery] = useState('')
  const { results, error, searching } = useStockSearch(query)

  return (
    <section className="card stock-search">
      <h2>Find a stock</h2>
      <input
        type="search"
        placeholder="Company or ticker"
        aria-label="Search stocks"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        autoComplete="off"
      />
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {query.trim() && !searching && !error && results.length === 0 && (
        <p className="muted">No stocks match “{query.trim()}”.</p>
      )}
      {results.length > 0 && (
        <ul className={searching ? 'search-results stale' : 'search-results'}>
          {results.map((stock) => (
            <li key={stock.symbol}>
              <button
                type="button"
                className={stock.symbol === selectedSymbol ? 'result selected' : 'result'}
                title={stock.name}
                aria-pressed={stock.symbol === selectedSymbol}
                onClick={() => onSelect(stock.symbol)}
              >
                <span className="result-symbol">{stock.symbol}</span>
                <span className="result-name">{stock.name}</span>
                <span className="result-exchange muted">{stock.exchange}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}