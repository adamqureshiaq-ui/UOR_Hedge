from fastapi import FastAPI

from database import Base, engine
from routers import auth, portfolio, trading

# Create any missing database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance Society Broker API")

app.include_router(auth.router)
app.include_router(trading.router)
app.include_router(portfolio.router)


@app.get("/")
def home():
    return {"status": "Backend, Database, and Trading Engines are operational!"}