// One headline number with its label, e.g. "Cash  $9,100.00"
export default function StatTile({ label, children }) {
  return (
    <div className="stat-tile">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{children}</div>
    </div>
  )
}