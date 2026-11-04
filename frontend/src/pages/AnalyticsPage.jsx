import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import Change from '../components/Change.jsx'
import FanChart from '../components/FanChart.jsx'
import StatTile from '../components/StatTile.jsx'
import { formatMoney, formatPercent } from '../format.js'

const HORIZONS = [
  { days: 5, label: '1 week' },
  { days: 21, label: '1 month' },
  { days: 63, label: '3 months' },
  { days: 126, label: '6 months' },
  { days: 252, label: '1 year' },
]
const SIMULATION_COUNTS = [1000, 5000, 10000]
const PERCENTILE_ROWS = [
  ['p5', '5th percentile (bad case)'],
  ['p25', '25th percentile'],
  ['p50', 'Median'],
  ['p75', '75th percentile'],
  ['p95', '95th percentile (good case)'],
]

export default function AnalyticsPage() {
  const [days, setDays] = useState(21)
  const [simulations, setSimulations] = useState(1000)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [running, setRunning] = useState(false)

  async function runSimulation(event) {
    event.preventDefault()
    setRunning(true)
    setError('')
    try {
      setResult(await apiFetch('/analytics/monte-carlo', { method: 'POST', body: { days, simulations } }))
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const horizonLabel = (n) => HORIZONS.find((h) => h.days === n)?.label ?? `${n} trading days`
  const noHoldings = error.startsWith('You have no holdings')

  return (
    <div className="analytics">
      <h1>Monte Carlo simulation</h1>
      <p className="muted intro">
        Generates thousands of possible futures for your current portfolio, based on how your stocks moved over the
        past year, to show the range of outcomes you might face. It’s a way to understand risk, not a forecast.
      </p>

      <form className="card sim-controls" onSubmit={runSimulation}>
        <label>
          Time horizon
          <select value={days} onChange={(event) => setDays(Number(event.target.value))}>
            {HORIZONS.map((h) => (
              <option key={h.days} value={h.days}>
                {h.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Simulations
          <select value={simulations} onChange={(event) => setSimulations(Number(event.target.value))}>
            {SIMULATION_COUNTS.map((n) => (
              <option key={n} value={n}>
                {n.toLocaleString()}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="primary-button" disabled={running}>
          {running ? `Running ${simulations.toLocaleString()} simulations…` : 'Run simulation'}
        </button>
      </form>

      {error && (
        <p className="error" role="alert">
          {error} {noHoldings && <Link to="/trade">Go to Trade</Link>}
        </p>
      )}

      {result && (
        // While a new run is in progress, the previous result stays visible but faded
        <div className={running ? 'sim-result stale' : 'sim-result'} aria-busy={running}>
          <div className="stat-row">
            <StatTile label="Median outcome">
              {formatMoney(result.final_value_percentiles.p50)}
              <div className="tile-sub">
                <Change amount={result.final_value_percentiles.p50 - result.starting_value} />
              </div>
            </StatTile>
            <StatTile label="Likely range (middle 90%)">
              <span className="range-value">
                {formatMoney(result.final_value_percentiles.p5)} – {formatMoney(result.final_value_percentiles.p95)}
              </span>
            </StatTile>
            <StatTile label="Chance of a loss">{formatPercent(result.probability_of_loss)}</StatTile>
            <StatTile label="Value at risk (95%)">
              {formatMoney(result.value_at_risk_95)}
              <div className="tile-sub muted">In 19 of 20 futures you lose less than this</div>
            </StatTile>
          </div>

          <section className="card">
            <h2>
              Your portfolio over the next {horizonLabel(result.days)}, starting from {formatMoney(result.starting_value)}
            </h2>
            <FanChart startingValue={result.starting_value} projection={result.projection} />
          </section>

          <section className="card">
            <h2>Where the {result.simulations.toLocaleString()} simulated futures ended</h2>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Outcome</th>
                    <th scope="col">Portfolio value</th>
                    <th scope="col">Change from today</th>
                  </tr>
                </thead>
                <tbody>
                  {PERCENTILE_ROWS.map(([key, label]) => (
                    <tr key={key}>
                      <th scope="row">{label}</th>
                      <td>{formatMoney(result.final_value_percentiles[key])}</td>
                      <td>
                        <Change amount={result.final_value_percentiles[key] - result.starting_value} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <details className="day-table">
              <summary>Show the chart’s data day by day</summary>
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Day</th>
                      <th scope="col">Worst 5%</th>
                      <th scope="col">Median</th>
                      <th scope="col">Best 5%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.projection.map((point) => (
                      <tr key={point.day}>
                        <th scope="row">{point.day}</th>
                        <td>{formatMoney(point.p5)}</td>
                        <td>{formatMoney(point.p50)}</td>
                        <td>{formatMoney(point.p95)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </section>

          <section className="card assumptions">
            <h2>How to read this</h2>
            <p>{result.assumptions}</p>
            <p className="muted">
              Based on {result.historical_days_used} days of price history · {result.simulations.toLocaleString()}{' '}
              simulations · Running it again gives slightly different numbers, because each run is random.
            </p>
          </section>
        </div>
      )}
    </div>
  )
}