from contextlib import asynccontextmanager

from fastapi import FastAPI

from corporate_actions import catch_up_on_startup
from database import Base, engine
from routers import (
    analytics,
    auth,
    leaderboard,
    market,
    portfolio,
    trading,
)

# Create any missing database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts, before it accepts requests."""
    catch_up_on_startup()  # apply any stock splits missed while the server was off
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