from contextlib import asynccontextmanager

from fastapi import FastAPI

from corporate_actions import catch_up_on_startup
from database import upgrade_database
from routers import (
    analytics,
    auth,
    leaderboard,
    market,
    portfolio,
    trading,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts, before it accepts requests."""
    upgrade_database()  # apply any new migrations (creates every table on a brand-new database)
    catch_up_on_startup()  # apply any splits and dividends missed while the server was off
    yield


app = FastAPI(title="Finance Society Broker API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(trading.router)
app.include_router(portfolio.router)
app.include_router(leaderboard.router)
app.include_router(analytics.router)
app.include_router(market.router)


@app.get("/")
def home():
    return {"status": "Backend, Database, and Trading Engines are operational!"}