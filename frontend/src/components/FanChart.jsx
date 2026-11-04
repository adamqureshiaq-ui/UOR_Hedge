import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatMoney, formatMoneyCompact } from '../format.js'

// The hover readout: one row per line, value first (strong), name second (muted), keyed by a short stroke
function FanTooltip({ active, payload }) {
  if (!active || !payload?.length) {
    return null
  }
  const point = payload[0].payload
  return (
    <div className="chart-tooltip">
      <div className="muted">{point.day === 0 ? 'Today' : `Day ${point.day}`}</div>
      <div className="tooltip-row">
        <span className="key band-key" />
        <strong>{formatMoney(point.p95)}</strong> <span className="muted">best 5%</span>
      </div>
      <div className="tooltip-row">
        <span className="key line-key" />
        <strong>{formatMoney(point.p50)}</strong> <span className="muted">median</span>
      </div>
      <div className="tooltip-row">
        <span className="key band-key" />
        <strong>{formatMoney(point.p5)}</strong> <span className="muted">worst 5%</span>
      </div>
    </div>
  )
}

// Fan chart: the shaded band holds the middle 90% of simulated futures, the line is the median
export default function FanChart({ startingValue, projection }) {
  // Start the fan at today's value so every path visibly begins from the same point
  const data = [{ day: 0, p5: startingValue, p50: startingValue, p95: startingValue }, ...projection].map((point) => ({
    ...point,
    band: [point.p5, point.p95],
  }))

  return (
    <figure className="fan-chart">
      <ul className="chart-legend" aria-hidden="true">
        <li>
          <span className="key line-key" /> Median outcome
        </li>
        <li>
          <span className="key band-swatch" /> Middle 90% of outcomes
        </li>
        <li>
          <span className="key start-key" /> Today’s value
        </li>
      </ul>
      {/* Height includes the axis labels, so the card never needs its own scrollbar */}
      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis
            dataKey="day"
            type="number"
            domain={[0, 'dataMax']}
            tickFormatter={(day) => (day === 0 ? 'Today' : `Day ${day}`)}
            stroke="var(--muted)"
            tick={{ fill: 'var(--muted)', fontSize: 12 }}
            tickLine={false}
          />
          <YAxis
            domain={['auto', 'auto']}
            tickFormatter={formatMoneyCompact}
            stroke="var(--muted)"
            tick={{ fill: 'var(--muted)', fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={64}
          />
          <Tooltip content={<FanTooltip />} cursor={{ stroke: 'var(--muted)', strokeWidth: 1 }} />
          <Area
            dataKey="band"
            stroke="none"
            fill="var(--accent)"
            fillOpacity={0.12}
            isAnimationActive={false}
            activeDot={false}
          />
          <ReferenceLine
            y={startingValue}
            stroke="var(--muted)"
            strokeDasharray="4 4"
            label={{ value: 'Today', position: 'insideTopLeft', fill: 'var(--muted)', fontSize: 12 }}
          />
          <Line
            dataKey="p50"
            stroke="var(--accent)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </figure>
  )
}