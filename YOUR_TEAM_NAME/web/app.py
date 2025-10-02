# app.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import asyncpg

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Настрой БД (Postgres, SQLite и т.п.)
DSN = "postgresql://tracker:secret@localhost/tracker"

@app.on_event("startup")
async def startup():
    app.state.pool = await asyncpg.create_pool(DSN)

@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/positions")
async def get_positions(limit: int = 100):
    query = "SELECT x, y, ts FROM positions ORDER BY ts ASC LIMIT $1"
    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch(query, limit)
    return [{"x": r["x"], "y": r["y"], "ts": r["ts"].isoformat()} for r in rows]
