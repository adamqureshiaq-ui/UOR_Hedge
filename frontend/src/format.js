// Number formatting used across the app, so every screen shows money the same way

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
const shares = new Intl.NumberFormat('en-US', { maximumFractionDigits: 4 })
const percent = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function formatMoney(value) {
  return money.format(value)
}

// "+$50.00", "−$12.30" or "$0.00" (a real minus sign, not a hyphen)
export function formatSignedMoney(value) {
  return `${sign(value)}${money.format(Math.abs(value))}`
}

// "+10.00%", "−3.25%" or "0.00%"
export function formatSignedPercent(value) {
  return `${sign(value)}${percent.format(Math.abs(value))}%`
}

export function formatPercent(value) {
  return `${percent.format(value)}%`
}

export function formatShares(value) {
  return shares.format(value)
}

function sign(value) {
  if (value > 0) return '+'
  if (value < 0) return '−'
  return ''
}