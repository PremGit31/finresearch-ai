# 📊 FinResearch AI — Financial Research & Analysis Agent

An AI-powered multi-agent system that researches companies, reads financial reports, retrieves real-time market data, and produces institutional-quality investment research reports with full citations.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-0.4-green)
![Gemini](https://img.shields.io/badge/Google-Gemini_2.0_Flash-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## 🏗️ Architecture

User Query → FastAPI/Streamlit
↓
┌─── LangGraph Workflow ───┐
│ │
│ 🔍 Researcher Node │ ← RAG + Tools (yfinance, SEC, News)
│ ↓ │
│ 🧠 Analyst Node │ ← Financial Analysis + Calculator
│ ↓ │
│ ✅ Fact-Checker Node │ ← Claim Verification
│ ↓ (loop?) │
│ 📝 Report Writer Node │ ← Citation-Backed Report
│ │
└──────────────────────────┘
↓
Final Research Report + Citations


## ✨ Key Features

### Multi-Agent Research Pipeline (LangGraph)
- **Researcher**: Gathers data from 6+ sources using tool calling
- **Analyst**: Performs deep financial analysis with calculation tools
- **Fact-Checker**: Validates claims against source data
- **Report Writer**: Compiles institutional-quality research reports

### RAG over Financial Documents
- Ingest annual reports, earnings call transcripts, SEC filings (PDF, HTML, TXT)
- Intelligent chunking with financial section awareness (Item 1, Item 7, etc.)
- Vector search via Qdrant with metadata filtering
- Google text-embedding-004 for embeddings

### Tool Calling
- **Stock Prices**: Real-time quotes via yfinance (no API key needed)
- **Financial Ratios**: P/E, ROE, margins, growth rates, 20+ metrics
- **News Search**: Google News RSS + NewsAPI + Yahoo Finance RSS
- **Financial Calculator**: DCF, CAGR, WACC, present value calculations
- **SEC Filings**: Direct EDGAR API integration for 10-K, 10-Q, 8-K
- **Document Search**: RAG-powered search over ingested documents

### MCP Servers
- Financial data server exposing stock quotes and company financials
- Document search server for RAG capabilities
- Compatible with Claude Desktop and other MCP clients

### Citations
- Every claim linked to source documents
- Citation tracker with relevance scores
- Full bibliography in generated reports

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker (for Qdrant)
- Google Gemini API key ([get free key](https://aistudio.google.com/apikey))

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/finresearch-ai.git
cd finresearch-ai

python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

pip install -r requirements.txt