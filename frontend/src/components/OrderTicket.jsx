import { useState } from 'react'
import { apiFetch } from '../api.js'
import { formatMoney, formatShares } from '../format.js'

// Buy/sell form for one stock, with a review step before any money moves
export default function OrderTicket({ quote, cash, sharesOwned, onTraded }) {
  const [side, setSide] = useState('buy')
  const [quantityText, setQuantityText] = useState('')
  const [reviewing, setReviewing] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const symbol = quote.symbol
  const price = side === 'buy' ? quote.ask_price : quote.bid_price
  const quantity = Number(quantityText)
  const validQuantity = quantityText !== '' && Number.isFinite(quantity) && quantity > 0
  const estimate = validQuantity && price !== null ? quantity * price : null

  // Problems we can spot before sending the order (the backend checks these again)
  let problem = ''
  if (price === null) {
    problem = `No live ${side === 'buy' ? 'ask' : 'bid'} price right now, so orders can't be placed.`
  } else if (quantityText !== '' && !validQuantity) {
    problem = 'Enter a quantity greater than 0.'
  } else if (side === 'buy' && estimate !== null && estimate > cash) {
    problem = `That would cost about ${formatMoney(estimate)}, but you have ${formatMoney(cash)} in cash.`
  } else if (side === 'sell' && validQuantity && quantity > sharesOwned) {
    problem = `You own ${formatShares(sharesOwned)} ${symbol} share${sharesOwned === 1 ? '' : 's'}.`
  }

  function changeSide(newSide) {
    setSide(newSide)
    setReviewing(false)
    setError('')
  }

  function changeQuantity(event) {
    setQuantityText(event.target.value)
    setReviewing(false)
    setError('')
  }

  async function placeOrder() {
    setSubmitting(true)
    setError('')
    try {
      const response = await apiFetch(`/trade/${side}`, { method: 'POST', body: { symbol, quantity } })
      setResult({ ...response, side })
      setQuantityText('')
      setReviewing(false)
      onTraded() // refresh the cash, position and quote shown on the page
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="card order-ticket">
      <h2>Place an order</h2>

      <div className="side-toggle" role="group" aria-label="Order side">
        <button type="button" aria-pressed={side === 'buy'} onClick={() => changeSide('buy')}>
          Buy
        </button>
        <button type="button" aria-pressed={side === 'sell'} onClick={() => changeSide('sell')}>
          Sell
        </button>
      </div>

      <label>
        Shares
        <div className="quantity-row">
          <input
            type="number"
            inputMode="decimal"
            min="0"
            step="any"
            placeholder="0"
            value={quantityText}
            onChange={changeQuantity}
          />
          {side === 'sell' && sharesOwned > 0 && (
            <button
              type="button"
              className="secondary-button"
              onClick={() => changeQuantity({ target: { value: String(sharesOwned) } })}
            >
              Sell all
            </button>
          )}
        </div>
      </label>

      <dl className="order-summary">
        <div>
          <dt>{side === 'buy' ? 'Price (ask)' : 'Price (bid)'}</dt>
          <dd>{price !== null ? formatMoney(price) : '—'}</dd>
        </div>
        <div>
          <dt>{side === 'buy' ? 'Estimated cost' : 'Estimated proceeds'}</dt>
          <dd>{estimate !== null ? formatMoney(estimate) : '—'}</dd>
        </div>
      </dl>

      {problem && <p className="notice">{problem}</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {!reviewing ? (
        <button
          type="button"
          className="primary-button"
          disabled={!validQuantity || Boolean(problem)}
          onClick={() => setReviewing(true)}
        >
          Review order
        </button>
      ) : (
        <div className="review" role="region" aria-label="Review order">
          <p>
            <strong>
              {side === 'buy' ? 'Buy' : 'Sell'} {formatShares(quantity)} {symbol}
            </strong>{' '}
            for about {formatMoney(estimate)}.
          </p>
          <p className="muted">
            The final price is the live {side === 'buy' ? 'ask' : 'bid'} when your order is placed, so it can differ
            slightly from this estimate.
          </p>
          <div className="review-actions">
            <button type="button" className="secondary-button" onClick={() => setReviewing(false)} disabled={submitting}>
              Cancel
            </button>
            <button type="button" className="primary-button" onClick={placeOrder} disabled={submitting}>
              {submitting ? 'Placing order…' : `Confirm ${side}`}
            </button>
          </div>
        </div>
      )}

      {result && (
        <p className="success" role="status">
          {result.side === 'buy' ? 'Bought' : 'Sold'} {formatShares(result.quantity)} {result.symbol} at{' '}
          {formatMoney(result.price_per_share)} for {formatMoney(result.total_cost)}. Cash now{' '}
          {formatMoney(result.remaining_cash)}.
        </p>
      )}
    </section>
  )
}