# src/tools/sec_filings.py
"""
SEC EDGAR filings retrieval tool.
Uses the free SEC EDGAR API (EDGAR Full-Text Search).
"""
import httpx
from langchain_core.tools import tool
from config.settings import SEC_USER_AGENT


@tool
def get_sec_filings(
    ticker: str,
    filing_type: str = "10-K",
    max_results: int = 5,
) -> str:
    """
    Search for SEC filings (10-K, 10-Q, 8-K, etc.) for a given company.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        filing_type: SEC filing type — '10-K', '10-Q', '8-K', 'DEF 14A', etc.
        max_results: Maximum number of filings to return

    Returns:
        List of recent SEC filings with dates, descriptions, and links.
    """
    try:
        # Step 1: Get CIK number from ticker
        headers = {"User-Agent": SEC_USER_AGENT}

        cik_url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2020-01-01&forms={filing_type}"
        
        # Use the EDGAR full-text search API
        search_url = "https://efts.sec.gov/LATEST/search-index"
        params = {
            "q": f'"{ticker}"',
            "forms": filing_type,
            "dateRange": "custom",
            "startdt": "2020-01-01",
        }

        # Alternative: use the company tickers JSON
        tickers_url = "https://www.sec.gov/files/company_tickers.json"
        resp = httpx.get(tickers_url, headers=headers, timeout=10)
        resp.raise_for_status()
        tickers_data = resp.json()

        cik = None
        for entry in tickers_data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                cik = str(entry["cik_str"]).zfill(10)
                company_name = entry.get("title", ticker)
                break

        if not cik:
            return f"Could not find CIK for ticker: {ticker}"

        # Step 2: Get filings from EDGAR submissions API
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = httpx.get(submissions_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        descriptions = recent.get("primaryDocDescription", [])
        primary_docs = recent.get("primaryDocument", [])

        # Filter by filing type
        results = []
        for i in range(len(forms)):
            if forms[i] == filing_type:
                accession_clean = accessions[i].replace("-", "")
                filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{cik.lstrip('0')}/{accession_clean}/{primary_docs[i]}"
                )
                results.append({
                    "form": forms[i],
                    "date": dates[i],
                    "description": descriptions[i] if i < len(descriptions) else "",
                    "accession": accessions[i],
                    "url": filing_url,
                })
                if len(results) >= max_results:
                    break

        if not results:
            return f"No {filing_type} filings found for {ticker}."

        output = f"**SEC {filing_type} Filings — {company_name} ({ticker.upper()})**\n\n"
        for i, filing in enumerate(results, 1):
            output += f"{i}. **{filing['form']}** — Filed: {filing['date']}\n"
            output += f"   Description: {filing['description']}\n"
            output += f"   Accession: {filing['accession']}\n"
            output += f"   URL: {filing['url']}\n\n"

        return output

    except Exception as e:
        return f"Error fetching SEC filings for {ticker}: {str(e)}"