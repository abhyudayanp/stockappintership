"""
portfolio.py
In-memory portfolio management (JSON file-backed for simplicity; swap with MongoDB in prod).
Tracks user holdings, calculates P&L and basic risk metrics.
"""

import json
import os
import yfinance as yf
from datetime import datetime

# Store in a /data subdirectory, fallback to /tmp for read-only environments (like Render)
try:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError:
    DATA_DIR = "/tmp/data"
    os.makedirs(DATA_DIR, exist_ok=True)
    
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio_data.json")


def _load() -> dict:
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {"holdings": []}


def _save(data: dict):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_holding(ticker: str, shares: float, buy_price: float):
    data = _load()
    for h in data["holdings"]:
        if h["ticker"].upper() == ticker.upper():
            # Average down / up
            total_cost = h["shares"] * h["buy_price"] + shares * buy_price
            h["shares"] += shares
            h["buy_price"] = total_cost / h["shares"]
            _save(data)
            return
    data["holdings"].append({
        "ticker": ticker.upper(),
        "shares": shares,
        "buy_price": buy_price,
        "added_on": datetime.utcnow().isoformat()
    })
    _save(data)


def remove_holding(ticker: str):
    data = _load()
    data["holdings"] = [h for h in data["holdings"] if h["ticker"].upper() != ticker.upper()]
    _save(data)


def get_portfolio() -> list:
    """
    Returns enriched list of holdings with live price, market value, P&L.
    """
    data = _load()
    result = []
    total_value = 0
    total_cost = 0

    for h in data["holdings"]:
        ticker = h["ticker"]
        try:
            info = yf.Ticker(ticker).fast_info
            current_price = float(info.last_price)
        except Exception:
            current_price = h["buy_price"]

        market_value = current_price * h["shares"]
        cost_basis = h["buy_price"] * h["shares"]
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0

        total_value += market_value
        total_cost += cost_basis

        result.append({
            "ticker": ticker,
            "shares": h["shares"],
            "buy_price": round(h["buy_price"], 2),
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "added_on": h.get("added_on", ""),
        })

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

    summary = {
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
    }

    return result, summary
