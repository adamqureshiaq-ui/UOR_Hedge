import { Link } from 'react-router-dom'
import Change from '../components/Change.jsx'
import StatTile from '../components/StatTile.jsx'
import { formatMoney, formatPercent, formatShares } from '../format.js'
import { usePortfolio } from '../hooks/usePortfolio.js'

export default function DashboardPage() {
  const { portfolio, error, refreshing, updatedAt, refresh } = usePortfolio()

  if (!portfolio) {
    return error ? (
      <p className="error" role="alert">
        Could not load your portfolio: {error}
      </p>
    ) : (
      <p className="muted">Loading your portfolio…</p>
    )
  }

  const { cash_balance, holdings_value, total_equity, holdings } = portfolio
  const unrealized = holdings.reduce((total, holding) => total + holding.unrealized_profit_loss, 0)
  const costBasis = holdings.reduce((total, holding) => total + holding.quantity * holding.average_buy_price, 0)

  return (
    // While refreshing, the previous numbers stay on screen, slightly faded, instead of flashing a spinner
    <div className={refreshing ? 'dashboard refreshing' : 'dashboard'} aria-busy={refreshing}>
      <div className="dashboard-header">
        <div>
          <div className="stat-label">Total equity</div>
          <div className="hero-figure">{formatMoney(total_equity)}</div>
        </div>
        <div className="refresh">
          {updatedAt && <span className="muted">Updated {updatedAt.toLocaleTimeString()}</span>}
          <button type="button" className="secondary-button" onClick={refresh} disabled={refreshing}>
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <p className="error" role="alert">
          Showing the last prices we received. {error}
        </p>
      )}

      <div className="stat-row">
        <StatTile label="Cash">{formatMoney(cash_balance)}</StatTile>
        <StatTile label="Invested">{formatMoney(holdings_value)}</StatTile>
        <StatTile label="Unrealized P/L">
          <Change amount={unrealized} percent={costBasis > 0 ? (unrealized / costBasis) * 100 : undefined} />
        </StatTile>
      </div>

      <section className="card">
        <h2>Holdings</h2>
        {holdings.length === 0 ? (
          <p className="muted">
            You don’t own any stocks yet. <Link to="/trade">Make your first trade</Link> to start building your
            portfolio.
          </p>
        ) : (
          <div className="table-scroll">
            <table className="holdings-table">
              <thead>
                <tr>
                  <th scope="col">Symbol</th>
                  <th scope="col">Shares</th>
                  <th scope="col">Avg cost</th>
                  <th scope="col">Price</th>
                  <th scope="col">Market value</th>
                  <th scope="col">Unrealized P/L</th>
                  <th scope="col">% of portfolio</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((holding) => {
                  const cost = holding.quantity * holding.average_buy_price
                  return (
                    <tr key={holding.symbol}>
                      <th scope="row">{holding.symbol}</th>
                      <td>{formatShares(holding.quantity)}</td>
                      <td>{formatMoney(holding.average_buy_price)}</td>
                      <td>{formatMoney(holding.current_price)}</td>
                      <td>{formatMoney(holding.market_value)}</td>
                      <td>
                        <Change
                          amount={holding.unrealized_profit_loss}
                          percent={cost > 0 ? (holding.unrealized_profit_loss / cost) * 100 : undefined}
                        />
                      </td>
                      <td>{formatPercent((holding.market_value / total_equity) * 100)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}