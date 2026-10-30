import { formatMoney } from '../format.js'

// Live prices for the selected stock: what you'd pay (ask) and what you'd get (bid)
export default function QuotePanel({ symbol, quote, error, loading, updatedAt, onRefresh }) {
  if (error) {
    return (
      <section className="card">
        <h2>{symbol}</h2>
        <p className="error" role="alert">
          {error}
        </p>
      </section>
    )
  }
  if (!quote) {
    return (
      <section className="card">
        <h2>{symbol}</h2>
        <p className="muted">Loading live prices…</p>
      </section>
    )
  }

  const marketClosed = quote.bid_price === null || quote.ask_price === null

  return (
    <section className={loading ? 'card quote stale' : 'card quote'}>
      <div className="quote-header">
        <h2>{quote.symbol}</h2>
        <div className="refresh">
          {updatedAt && <span className="muted">Updated {updatedAt.toLocaleTimeString()}</span>}
          <button type="button" className="secondary-button" onClick={onRefresh}>
            Refresh
          </button>
        </div>
      </div>
      <div className="quote-grid">
        <div>
          <div className="stat-label">Buy at (ask)</div>
          <div className="stat-value">{quote.ask_price !== null ? formatMoney(quote.ask_price) : '—'}</div>
        </div>
        <div>
          <div className="stat-label">Sell at (bid)</div>
          <div className="stat-value">{quote.bid_price !== null ? formatMoney(quote.bid_price) : '—'}</div>
        </div>
        <div>
          <div className="stat-label">Last trade</div>
          <div className="stat-value">{formatMoney(quote.last_trade_price)}</div>
        </div>
        <div>
          <div className="stat-label">Spread</div>
          <div className="stat-value">{quote.spread !== null ? formatMoney(quote.spread) : '—'}</div>
        </div>
      </div>
      {marketClosed && (
        <p className="notice">
          No live buy or sell price right now — the market may be closed. US stocks trade 9:30am–4pm New York time (2:30pm-9pm GMT),
          Monday to Friday.
        </p>
      )}
    </section>
  )
}