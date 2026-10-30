import { useAuth } from '../auth/useAuth.js'
import { formatMoney, formatSignedPercent } from '../format.js'
import { useLeaderboard } from '../hooks/useLeaderboard.js'

const TOP_COUNT = 50

// A return like "▲ +5.20%": sign + arrow + colour, never colour alone
function Return({ percent }) {
  const direction = percent > 0 ? 'up' : percent < 0 ? 'down' : 'flat'
  const arrow = { up: '▲ ', down: '▼ ', flat: '' }[direction]
  return (
    <span className={`change ${direction}`}>
      {arrow && <span aria-hidden="true">{arrow}</span>}
      {formatSignedPercent(percent)}
    </span>
  )
}

function Row({ entry, isMe }) {
  return (
    <tr className={isMe ? 'me' : undefined} aria-current={isMe ? 'true' : undefined}>
      <td className="rank">{entry.rank}</td>
      <th scope="row">
        {entry.username}
        {isMe && <span className="you"> (you)</span>}
      </th>
      <td>{formatMoney(entry.total_equity)}</td>
      <td>
        <Return percent={entry.return_percent} />
      </td>
    </tr>
  )
}

export default function LeaderboardPage() {
  const { user } = useAuth()
  const { leaderboard, error, refreshing, updatedAt, refresh } = useLeaderboard()

  if (!leaderboard) {
    return error ? (
      <p className="error" role="alert">
        Could not load the leaderboard: {error}
      </p>
    ) : (
      <p className="muted">Loading the leaderboard…</p>
    )
  }

  const { entries, my_rank, total_members } = leaderboard
  const me = entries.find((entry) => entry.username === user.username)
  const top = entries.slice(0, TOP_COUNT)
  const meOutsideTop = me && !top.includes(me)

  return (
    <div className={refreshing ? 'leaderboard refreshing' : 'leaderboard'} aria-busy={refreshing}>
      <div className="dashboard-header">
        <h1>Society leaderboard</h1>
        <div className="refresh">
          {updatedAt && <span className="muted">Updated {updatedAt.toLocaleTimeString()}</span>}
          <button type="button" className="secondary-button" onClick={refresh} disabled={refreshing}>
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <p className="error" role="alert">
          Showing the last standings we received. {error}
        </p>
      )}

      <section className="stat-row">
        <div className="stat-tile">
          <div className="stat-label">Your rank</div>
          <div className="stat-value">
            #{my_rank} <span className="muted of-total">of {total_members}</span>
          </div>
        </div>
        {me && (
          <>
            <div className="stat-tile">
              <div className="stat-label">Your total equity</div>
              <div className="stat-value">{formatMoney(me.total_equity)}</div>
            </div>
            <div className="stat-tile">
              <div className="stat-label">Your return</div>
              <div className="stat-value">
                <Return percent={me.return_percent} />
              </div>
            </div>
          </>
        )}
      </section>

      <section className="card">
        <h2>{total_members > TOP_COUNT ? `Top ${TOP_COUNT}` : 'Standings'}</h2>
        <p className="muted">Ranked by total equity (cash + live value of holdings). Everyone starts with $10,000.</p>
        <div className="table-scroll">
          <table className="leaderboard-table">
            <thead>
              <tr>
                <th scope="col">Rank</th>
                <th scope="col">Member</th>
                <th scope="col">Total equity</th>
                <th scope="col">Return</th>
              </tr>
            </thead>
            <tbody>
              {top.map((entry) => (
                <Row key={entry.username} entry={entry} isMe={entry === me} />
              ))}
              {meOutsideTop && (
                <>
                  <tr className="gap" aria-hidden="true">
                    <td colSpan={4}>…</td>
                  </tr>
                  <Row entry={me} isMe />
                </>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}