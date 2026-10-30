import { useSearchParams } from 'react-router-dom'
import OrderTicket from '../components/OrderTicket.jsx'
import QuotePanel from '../components/QuotePanel.jsx'
import StockSearch from '../components/StockSearch.jsx'
import { formatMoney, formatShares } from '../format.js'
import { usePortfolio } from '../hooks/usePortfolio.js'
import { useQuote } from '../hooks/useQuote.js'

export default function TradePage() {
  // The selected stock lives in the URL (/trade?symbol=AAPL), so links and page refreshes keep it
  const [searchParams, setSearchParams] = useSearchParams()
  const symbol = searchParams.get('symbol')?.toUpperCase() ?? null

  const quoteState = useQuote(symbol)
  const { portfolio, refresh: refreshPortfolio } = usePortfolio()

  const cash = portfolio?.cash_balance ?? 0
  const holding = portfolio?.holdings.find((h) => h.symbol === symbol)
  const sharesOwned = holding?.quantity ?? 0

  function handleTraded() {
    refreshPortfolio()
    quoteState.reload()
  }

  return (
    <div className="trade-page">
      <h1>Trade</h1>
      <div className="trade-layout">
        <StockSearch selectedSymbol={symbol} onSelect={(picked) => setSearchParams({ symbol: picked })} />

        <div className="trade-main">
          {!symbol ? (
            <section className="card">
              <p className="muted">Search for a stock to see its live price and place an order.</p>
            </section>
          ) : (
            <>
              <QuotePanel symbol={symbol} {...quoteState} onRefresh={quoteState.reload} />

              <section className="card position">
                <div>
                  <div className="stat-label">Cash available</div>
                  <div className="stat-value">{portfolio ? formatMoney(cash) : '…'}</div>
                </div>
                <div>
                  <div className="stat-label">You own</div>
                  <div className="stat-value">
                    {portfolio ? `${formatShares(sharesOwned)} ${symbol}` : '…'}
                  </div>
                </div>
              </section>

              {quoteState.quote && portfolio && (
                // key={symbol}: switching stocks gives a fresh, empty order form
                <OrderTicket
                  key={symbol}
                  quote={quoteState.quote}
                  cash={cash}
                  sharesOwned={sharesOwned}
                  onTraded={handleTraded}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}