"""
app.py — AI-Powered Stock Intelligence Platform
Main Flask application. Orchestrates:
  - News sentiment (FinBERT via Alpha Vantage)
  - Technical analysis (RSI, MACD, BB, SMA via yfinance)
  - AI Market Outlook (composite score)
  - Portfolio tracker (JSON-backed)
"""

import json
import logging
import os

# Render deployment fix: Make sure yfinance caches to /tmp where it has write access
os.environ["YFINANCE_CACHE_DIR"] = "/tmp/yfinance"

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytz
from flask import Flask, jsonify, render_template, request
from plotly.utils import PlotlyJSONEncoder

import alpha_api as API
from portfolio import add_holding, get_portfolio, remove_holding
from sentiment.FinbertSentiment import FinbertSentiment
from technical_analysis import build_technical_chart, get_technical_indicators

# ── Setup ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

EST = pytz.timezone("US/Eastern")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "stock-intelligence-secret-key-2024")

sentimentAlgo = FinbertSentiment()


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_news(ticker: str) -> pd.DataFrame:
    sentimentAlgo.set_symbol(ticker)
    return API.get_news(ticker)


def score_news(news_df: pd.DataFrame) -> pd.DataFrame:
    if news_df.empty or "title" not in news_df.columns:
        return pd.DataFrame()
    sentimentAlgo.set_data(news_df)
    sentimentAlgo.calc_sentiment_score()
    return sentimentAlgo.df


def plot_sentiment(df: pd.DataFrame) -> go.Figure:
    return sentimentAlgo.plot_sentiment()


def get_earliest_date(df: pd.DataFrame) -> pd.Timestamp:
    return df["Date Time"].iloc[-1].to_pydatetime()


def plot_hourly_price(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure()
    if not df.empty:
        fig.add_trace(go.Scatter(
            x=[str(v) for v in df["Date Time"]],
            y=[float(v) for v in df["Price"]],
            mode="lines",
            line=dict(color="#636efa"),
            name="Price"
        ))
        
    fig.update_layout(
        title=f"{ticker} Price History",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,20,40,0.8)",
        font=dict(color="#e2e8f0", family="Inter, sans-serif"),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(
            rangeselector=dict(
                bgcolor="#1f2937",
                activecolor="#374151",
                font=dict(color="white"),
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            type="date"
        )
    )
    return fig


def convert_headline_to_link(df: pd.DataFrame) -> pd.DataFrame:
    if "title + link" in df.columns:
        df.insert(2, "Headline", df["title + link"])
        df.drop(columns=["sentiment", "title + link", "title"], inplace=True, errors="ignore")
    return df


def compute_ai_outlook(sentiment_score: float, rsi: float, macd_signal: str, price_vs_sma50: str) -> dict:
    """
    Combines sentiment + technicals into an AI market outlook score.
    Returns a dict with label, score (0-100), confidence, and description.
    """
    score = 50  # neutral baseline

    # Sentiment contribution (max ±25)
    score += sentiment_score * 25

    # RSI contribution
    if rsi > 70:
        score -= 15
    elif rsi < 30:
        score += 15
    elif rsi > 55:
        score += 5
    elif rsi < 45:
        score -= 5

    # MACD contribution
    score += 10 if macd_signal == "bullish" else -10

    # SMA50 contribution
    score += 5 if price_vs_sma50 == "above" else -5

    score = max(0, min(100, score))

    if score >= 70:
        label = "Strongly Bullish"
        color = "#00e5a0"
        emoji = "🚀"
    elif score >= 55:
        label = "Moderately Bullish"
        color = "#68d391"
        emoji = "📈"
    elif score >= 45:
        label = "Neutral / Hold"
        color = "#f6ad55"
        emoji = "⚖️"
    elif score >= 30:
        label = "Moderately Bearish"
        color = "#fc8181"
        emoji = "📉"
    else:
        label = "Strongly Bearish"
        color = "#ff4f6d"
        emoji = "🔻"

    rsi_label = "Overbought" if rsi > 70 else ("Oversold" if rsi < 30 else "Neutral")
    description = (
        f"Sentiment is {'positive' if sentiment_score > 0 else 'negative' if sentiment_score < 0 else 'neutral'} "
        f"({sentiment_score:+.2f}). RSI={rsi:.1f} ({rsi_label}). "
        f"MACD is {macd_signal}. Price is {price_vs_sma50} SMA-50."
    )

    return {
        "score": round(score, 1),
        "label": label,
        "color": color,
        "emoji": emoji,
        "description": description,
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    ticker = request.form.get("ticker", "").strip().upper()
    if not ticker:
        return render_template("index.html", error="Please enter a valid ticker.")

    logger.info(f"Analyzing ticker: {ticker}")

    # ── Sentiment ───────────────────────────────────────────
    try:
        news_df = get_news(ticker)
        scored_news_df = score_news(news_df)
    except Exception as e:
        logger.warning(f"Sentiment error: {e}")
        news_df = pd.DataFrame()
        scored_news_df = pd.DataFrame()

    avg_sentiment = 0.0
    if not scored_news_df.empty and "sentiment_score" in scored_news_df.columns:
        avg_sentiment = float(scored_news_df["sentiment_score"].mean())

    try:
        fig_sentiment = plot_sentiment(scored_news_df) if not scored_news_df.empty else go.Figure()
    except Exception:
        fig_sentiment = go.Figure()
    graph_sentiment = fig_sentiment.to_json(engine="json")

    # ── Price ────────────────────────────────────────────────
    try:
        earliest_dt = get_earliest_date(news_df) if not news_df.empty else None
        price_df = API.get_price_history(ticker, earliest_datetime=None)
        fig_price = plot_hourly_price(price_df, ticker) if not price_df.empty else go.Figure()
    except Exception as e:
        logger.warning(f"Price history error: {e}")
        price_df = pd.DataFrame()
        fig_price = go.Figure()
    graph_price = fig_price.to_json(engine="json")

    # ── Technical Analysis ───────────────────────────────────
    try:
        indicators = get_technical_indicators(ticker)
        tech_chart = build_technical_chart(indicators, ticker)
    except Exception as e:
        logger.warning(f"Technical analysis error: {e}")
        indicators = {}
        tech_chart = go.Figure()
    graph_tech = tech_chart.to_json(engine="json")

    rsi = indicators.get("rsi_current", 50.0)
    rsi_label = indicators.get("rsi_label", "neutral")
    macd_signal = indicators.get("macd_signal", "neutral")
    price_vs_sma50 = indicators.get("price_vs_sma50", "neutral")
    current_price = indicators.get("current_price", "N/A")

    # ── AI Outlook ───────────────────────────────────────────
    outlook = compute_ai_outlook(avg_sentiment, rsi, macd_signal, price_vs_sma50)

    # ── News Table ───────────────────────────────────────────
    display_df = pd.DataFrame()
    if not scored_news_df.empty:
        display_df = convert_headline_to_link(scored_news_df.copy())

    table_html = display_df.to_html(
        classes="news-table", render_links=True, escape=False, index=False
    ) if not display_df.empty else "<p class='no-data'>No news data available.</p>"

    return render_template(
        "analysis.html",
        ticker=ticker,
        current_price=current_price,
        graph_price=graph_price,
        graph_sentiment=graph_sentiment,
        graph_tech=graph_tech,
        table=table_html,
        rsi=rsi,
        rsi_label=rsi_label,
        macd_signal=macd_signal,
        price_vs_sma50=price_vs_sma50,
        avg_sentiment=round(avg_sentiment, 3),
        outlook=outlook,
    )


# ── Portfolio API ────────────────────────────────────────────────────────────

@app.route("/portfolio", methods=["GET"])
def portfolio():
    holdings, summary = get_portfolio()
    return render_template("portfolio.html", holdings=holdings, summary=summary)


@app.route("/api/portfolio/add", methods=["POST"])
def portfolio_add():
    data = request.get_json(force=True)
    ticker = data.get("ticker", "").strip().upper()
    shares = float(data.get("shares", 0))
    buy_price = float(data.get("buy_price", 0))
    if not ticker or shares <= 0 or buy_price <= 0:
        return jsonify({"error": "Invalid input"}), 400
    add_holding(ticker, shares, buy_price)
    return jsonify({"status": "ok", "ticker": ticker})


@app.route("/api/portfolio/remove", methods=["POST"])
def portfolio_remove():
    data = request.get_json(force=True)
    ticker = data.get("ticker", "").strip().upper()
    remove_holding(ticker)
    return jsonify({"status": "ok"})


# ── Health Check (for Docker/ALB) ────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "stock-intelligence-platform"}), 200


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
