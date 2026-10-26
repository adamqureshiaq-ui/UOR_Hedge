import { formatSignedMoney, formatSignedPercent } from '../format.js'

// A gain or loss: sign + arrow + colour, so it never relies on colour alone
export default function Change({ amount, percent }) {
  const direction = amount > 0 ? 'up' : amount < 0 ? 'down' : 'flat'
  const arrow = { up: '▲', down: '▼', flat: '' }[direction]

  return (
    <span className={`change ${direction}`}>
      {arrow && <span aria-hidden="true">{arrow} </span>}
      {formatSignedMoney(amount)}
      {percent !== undefined && <span className="change-percent"> ({formatSignedPercent(percent)})</span>}
    </span>
  )
}