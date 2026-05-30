# 📈 StockIQ — AI-Powered Stock Intelligence Platform

> **Cloud & DevOps Engineering Capstone Project**  
> *FinBERT Sentiment · RSI/MACD/Bollinger · AI Market Outlook · Portfolio Tracker · Docker · AWS ECS · GitHub Actions CI/CD*

---

## 🚀 Live Features

| Feature | Technology |
|---------|-----------|
| **News Sentiment Analysis** | FinBERT (HuggingFace Transformers) |
| **Technical Analysis** | RSI · MACD · Bollinger Bands · SMA 50/200 |
| **AI Market Outlook** | Composite score from sentiment + technicals |
| **Portfolio Tracker** | Live P&L with yfinance real-time prices |
| **Interactive Charts** | Plotly dark-mode candlestick + indicators |
| **Containerization** | Docker multi-stage build + Docker Compose |
| **Cloud Deployment** | AWS ECS Fargate + ECR |
| **CI/CD Pipeline** | GitHub Actions (Test → Build → Deploy) |
| **Monitoring** | AWS CloudWatch logs + health checks |

---

## 🏗️ Architecture

```
Browser → AWS ECS Fargate (Flask/Gunicorn)
                ├── Alpha Vantage API  (news + price)
                ├── yfinance           (RSI/MACD/BB)
                └── AWS CloudWatch     (monitoring)

GitHub Push → GitHub Actions → ECR → ECS Rolling Deploy
```

---

## ⚡ Quick Start (Local)

### With Docker (Recommended)

```bash
cd code/
docker compose up --build
```
Open http://localhost:5000

### Without Docker

```bash
cd code/
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py
```

---

## ☁️ Cloud Deployment (AWS)

See the full step-by-step guide in [deployment_guide.md](../deployment_guide.md).

**Short version:**
1. Create ECR repo + ECS cluster in AWS Console
2. Add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to GitHub Secrets
3. Push to `main` — GitHub Actions handles the rest automatically

---

## 🔄 CI/CD Pipeline

```
git push origin main
       ↓
[Job 1] Lint + Health Check Test
       ↓
[Job 2] docker build → push to ECR  
       ↓
[Job 3] Update ECS task definition → Rolling deploy
       ↓
✅ Live on AWS
```

---

## 📁 Project Structure

```
code/
├── app.py                  # Flask application (routes + orchestration)
├── technical_analysis.py   # RSI, MACD, Bollinger Bands engine
├── portfolio.py            # Portfolio P&L tracker
├── alpha_api.py            # Alpha Vantage integration
├── sentiment/
│   ├── FinbertSentiment.py # FinBERT NLP sentiment scoring
│   └── SentimentAnalysisBase.py
├── templates/
│   ├── index.html          # Landing page
│   ├── analysis.html       # Full analysis dashboard
│   └── portfolio.html      # Portfolio tracker
├── static/css/style.css    # Premium dark UI
├── Dockerfile              # Multi-stage production build
├── docker-compose.yml      # App + MongoDB orchestration
└── requirements.txt
.github/workflows/
└── deploy.yml              # GitHub Actions CI/CD
```

---

## 🛠️ Tech Stack

**Backend:** Python 3.11 · Flask · Gunicorn  
**AI/ML:** FinBERT (ProsusAI) · HuggingFace Transformers · PyTorch  
**Data:** Alpha Vantage API · yfinance (Yahoo Finance)  
**Frontend:** HTML5 · Vanilla CSS (glassmorphism dark mode) · Plotly.js  
**DevOps:** Docker · Docker Compose · GitHub Actions  
**Cloud:** AWS ECS Fargate · AWS ECR · AWS CloudWatch · AWS IAM  
**Database:** MongoDB (Docker Compose)

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Landing page |
| POST | `/analyze` | Full stock analysis |
| GET | `/portfolio` | Portfolio dashboard |
| POST | `/api/portfolio/add` | Add holding (JSON) |
| POST | `/api/portfolio/remove` | Remove holding (JSON) |
| GET | `/health` | Health check (ECS/ALB) |

---

*Built as a Cloud & DevOps Engineering Capstone demonstrating end-to-end production deployment.*
