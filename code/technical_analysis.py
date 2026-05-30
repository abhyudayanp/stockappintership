"""
technical_analysis.py
Computes RSI, MACD, Moving Averages, Bollinger Bands from yfinance data.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def get_ohlcv(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df.dropna(inplace=True)
    return df


def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=window - 1, min_periods=window).mean()
    avg_loss = loss.ewm(com=window - 1, min_periods=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_macd(series: pd.Series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram


def compute_bollinger_bands(series: pd.Series, window: int = 20):
    sma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    return upper, sma, lower


def get_technical_indicators(ticker: str) -> dict:
    """
    Returns a dict with:
      - df: the OHLCV dataframe with all indicators
      - rsi_current: latest RSI value
      - macd_signal: 'bullish' or 'bearish'
      - price_vs_sma50: 'above' or 'below'
      - summary: human-readable string
    """
    df = get_ohlcv(ticker)
    if df.empty:
        return {}

    close = df["Close"].squeeze()

    df["RSI"] = compute_rsi(close)
    df["MACD"], df["MACD_Signal"], df["MACD_Hist"] = compute_macd(close)
    df["BB_Upper"], df["SMA20"], df["BB_Lower"] = compute_bollinger_bands(close)
    df["SMA50"] = close.rolling(50).mean()
    df["SMA200"] = close.rolling(200).mean()

    latest = df.iloc[-1]

    rsi_val = float(latest["RSI"]) if not pd.isna(latest["RSI"]) else 50.0
    macd_val = float(latest["MACD"]) if not pd.isna(latest["MACD"]) else 0.0
    macd_sig = float(latest["MACD_Signal"]) if not pd.isna(latest["MACD_Signal"]) else 0.0
    sma50 = float(latest["SMA50"]) if not pd.isna(latest["SMA50"]) else float(latest["Close"])
    current_price = float(latest["Close"])

    macd_signal = "bullish" if macd_val > macd_sig else "bearish"
    price_vs_sma50 = "above" if current_price > sma50 else "below"

    rsi_label = "overbought" if rsi_val > 70 else ("oversold" if rsi_val < 30 else "neutral")

    return {
        "df": df,
        "rsi_current": round(rsi_val, 2),
        "rsi_label": rsi_label,
        "macd_signal": macd_signal,
        "price_vs_sma50": price_vs_sma50,
        "current_price": round(current_price, 2),
        "sma50": round(sma50, 2),
    }


def build_technical_chart(indicators: dict, ticker: str) -> go.Figure:
    """Creates an interactive multi-panel technical analysis chart."""
    if not indicators or "df" not in indicators:
        return go.Figure()

    df = indicators["df"]
    close = df["Close"].squeeze()

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.25, 0.20],
        vertical_spacing=0.04,
        subplot_titles=(f"{ticker} Price & Bands", "RSI (14)", "MACD"),
    )

    x_list = [str(v) for v in df.index]
    
    # --- Candlestick ---
    fig.add_trace(go.Candlestick(
        x=x_list,
        open=[float(v) for v in df["Open"].squeeze()],
        high=[float(v) for v in df["High"].squeeze()],
        low=[float(v) for v in df["Low"].squeeze()],
        close=[float(v) for v in close],
        name="OHLC",
        increasing_line_color="#00e5a0",
        decreasing_line_color="#ff4f6d",
    ), row=1, col=1)

    # Bollinger Bands
    fig.add_trace(go.Scatter(x=x_list, y=[float(v) for v in df["BB_Upper"].squeeze()], name="BB Upper",
                             line=dict(color="rgba(99,179,237,0.5)", dash="dot"), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=x_list, y=[float(v) for v in df["SMA20"].squeeze()], name="SMA 20",
                             line=dict(color="rgba(99,179,237,0.9)"), showlegend=True), row=1, col=1)
    fig.add_trace(go.Scatter(x=x_list, y=[float(v) for v in df["BB_Lower"].squeeze()], name="BB Lower",
                             line=dict(color="rgba(99,179,237,0.5)", dash="dot"),
                             fill="tonexty", fillcolor="rgba(99,179,237,0.08)", showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=x_list, y=[float(v) for v in df["SMA50"].squeeze()], name="SMA 50",
                             line=dict(color="#f6ad55")), row=1, col=1)

    # --- RSI ---
    fig.add_trace(go.Scatter(x=x_list, y=[float(v) for v in df["RSI"].squeeze()], name="RSI",
                             line=dict(color="#9f7aea")), row=2, col=1)
    fig.add_hline(y=70, line_color="rgba(255,79,109,0.6)", line_dash="dot", row=2, col=1)
    fig.add_hline(y=30, line_color="rgba(0,229,160,0.6)", line_dash="dot", row=2, col=1)

    # --- MACD ---
    colors = ["#00e5a0" if v >= 0 else "#ff4f6d" for v in df["MACD_Hist"].squeeze()]
    fig.add_trace(go.Bar(x=x_list, y=[float(v) for v in df["MACD_Hist"].squeeze()], name="Histogram",
                         marker_color=colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=x_list, y=[float(v) for v in df["MACD"].squeeze()], name="MACD Line",
                             line=dict(color="#63b3ed")), row=3, col=1)
    fig.add_trace(go.Scatter(x=x_list, y=[float(v) for v in df["MACD_Signal"].squeeze()], name="Signal",
                             line=dict(color="#f6ad55")), row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,20,40,0.8)",
        font=dict(color="#e2e8f0", family="Inter, sans-serif"),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        margin=dict(l=10, r=10, t=40, b=10),
    )

    return fig
