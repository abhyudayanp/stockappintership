"""
alpha_api.py — Data layer for StockIQ
Primary:  Finnhub (news + quote) — generous free tier, 60 calls/min
Fallback: yfinance for price history (always free, no key needed)
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf

# ── Finnhub free key (get yours at finnhub.io — takes 30 seconds, no card) ──
# Replace with your own key from https://finnhub.io/register
FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "d10ghl9r01qgqtum4aa0d10ghl9r01qgqtum4aag")

FINNHUB_BASE = "https://finnhub.io/api/v1"


# ── News ─────────────────────────────────────────────────────────────────────

def get_news(ticker: str) -> pd.DataFrame:
    """
    Fetches company news from Finnhub for the last 7 days.
    Returns a DataFrame with: title, link, time_published, summary, source, Date Time, title+link
    """
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)

    url = f"{FINNHUB_BASE}/company-news"
    params = {
        "symbol": ticker,
        "from": str(week_ago),
        "to": str(today),
        "token": FINNHUB_KEY,
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[Finnhub news ERROR] {e}")
        return pd.DataFrame()

    if not data or not isinstance(data, list):
        print(f"[Finnhub] No news returned for {ticker}: {data}")
        return pd.DataFrame()

    credible_sources = {"Yahoo", "Reuters", "Bloomberg", "CNBC", "MarketWatch", 
                        "Wall Street Journal", "Financial Times", "Forbes", "SeekingAlpha"}
    
    seen_titles = set()
    articles = []
    
    for a in data:
        title = a.get("headline", "")
        source = a.get("source", "")
        if source in credible_sources and title not in seen_titles:
            seen_titles.add(title)
            articles.append(a)
            if len(articles) == 20:
                break

    rows = []
    for a in articles:
        ts = a.get("datetime", 0)
        try:
            dt = datetime.utcfromtimestamp(ts)
        except Exception:
            dt = datetime.utcnow()

        title = a.get("headline", "")
        link  = a.get("url", "")
        rows.append({
            "title":          title,
            "time_published": str(dt),
            "summary":        a.get("summary", ""),
            "source":         a.get("source", ""),
            "Date Time":      pd.Timestamp(dt),
            "title + link":   f'<a href="{link}" target="_blank">{title}</a>',
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    return df


# ── Price History (yfinance — always free) ────────────────────────────────────

def get_price_history(ticker: str, earliest_datetime=None) -> pd.DataFrame:
    """
    Fetches intraday (hourly) price history using yfinance.
    Falls back to daily if intraday not available.
    earliest_datetime: if provided, filter to dates >= this value
    """
    try:
        # Try hourly first (last 730 days is max for 1h)
        df = yf.download(
            ticker, period="730d", interval="1h",
            progress=False, auto_adjust=True
        )

        if df.empty:
            raise ValueError("Empty hourly data")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        df = df.reset_index()
        df.rename(columns={"Datetime": "Date Time", "Date": "Date Time", "Close": "Price", "close": "Price"}, inplace=True)

        if "Date Time" not in df.columns and len(df.columns) > 0:
            df.rename(columns={df.columns[0]: "Date Time"}, inplace=True)

        df["Date Time"] = pd.to_datetime(df["Date Time"], utc=True).dt.tz_localize(None)

        if earliest_datetime is not None:
            try:
                cutoff = pd.Timestamp(earliest_datetime).tz_localize(None)
                df = df[df["Date Time"] >= cutoff]
            except Exception:
                pass

        return df[["Date Time", "Price"]].dropna()

    except Exception as e:
        print(f"[yfinance hourly ERROR] {e} — falling back to daily")
        try:
            df = yf.download(ticker, period="1y", interval="1d",
                             progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            df = df.reset_index()
            df.rename(columns={"Date": "Date Time"}, inplace=True)
            df["Price"] = pd.to_numeric(df.get("Close", pd.Series()), errors="coerce")
            df["Date Time"] = pd.to_datetime(df["Date Time"])
            return df[["Date Time", "Price"]].dropna()
        except Exception as e2:
            print(f"[yfinance daily ERROR] {e2}")
            return pd.DataFrame()
