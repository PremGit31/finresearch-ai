# ui/app.py
"""
Streamlit frontend for FinResearch AI.
"""
import streamlit as st
import httpx
import json
import time
from pathlib import Path

# Page config
st.set_page_config(
    page_title="FinResearch AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://api:8000"


def check_api_health():
    """Check if the API is running."""
    try:
        resp = httpx.get(f"{API_BASE}/health", timeout=5)
        return resp.json()
    except Exception:
        return None


def main():
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 1.5rem;
        color: white;
        text-align: center;
    }
    .report-section {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
    }
    .stProgress > div > div > div > div {
        background-color: #667eea;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<div class="main-header">📊 FinResearch AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">AI-Powered Financial Research & Analysis Agent</div>',
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # API Health
        health = check_api_health()
        if health:
            st.success(f"API Status: {health['status']}")
            services = health.get("services", {})
            for svc, status in services.items():
                if status == "healthy":
                    st.write(f"  ✅ {svc}")
                else:
                    st.write(f"  ⚠️ {svc}: {status}")
        else:
            st.error("API is not running. Start it with: `uvicorn api.main:app --reload`")

        st.divider()

        # Document Upload Section
        st.header("📄 Document Upload")
        uploaded_file = st.file_uploader(
            "Upload Financial Document",
            type=["pdf", "txt", "html", "htm", "md"],
            help="Upload annual reports, earnings transcripts, or SEC filings",
        )

        if uploaded_file:
            company = st.text_input("Company Name", key="upload_company")
            doc_type = st.selectbox(
                "Document Type",
                ["annual_report", "earnings_transcript", "10-K", "10-Q", "8-K", "other"],
                key="upload_type",
            )
            year = st.text_input("Year", key="upload_year")

            if st.button("📤 Upload & Index", key="upload_btn"):
                with st.spinner("Uploading and indexing document..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                        data = {}
                        if company:
                            data["company"] = company
                        if doc_type:
                            data["document_type"] = doc_type
                        if year:
                            data["year"] = year

                        resp = httpx.post(
                            f"{API_BASE}/documents/upload",
                            files=files,
                            data=data,
                            timeout=120,
                        )
                        if resp.status_code == 200:
                            result = resp.json()
                            st.success(
                                f"✅ Uploaded! {result['chunks_created']} chunks indexed."
                            )
                        else:
                            st.error(f"Upload failed: {resp.text}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        st.divider()

        # Document Store Info
        st.header("🗄️ Document Store")
        if st.button("Refresh Info", key="refresh_store"):
            try:
                resp = httpx.get(f"{API_BASE}/documents/info", timeout=10)
                if resp.status_code == 200:
                    info = resp.json()
                    st.metric("Documents Indexed", info.get("points_count", 0))
                    st.write(f"Status: {info.get('status', 'unknown')}")
            except Exception as e:
                st.warning(f"Could not fetch store info: {e}")

    # Main Content Area
    tab1, tab2, tab3 = st.tabs(["🔍 Research", "📈 Quick Quote", "📚 Document Search"])

    # Tab 1: Full Research Analysis
    with tab1:
        st.header("Investment Research Analysis")

        col1, col2 = st.columns([1, 3])

        with col1:
            ticker = st.text_input(
                "Ticker Symbol",
                value="AAPL",
                max_chars=10,
                help="Enter a stock ticker symbol",
            ).upper()

        with col2:
            query = st.text_area(
                "Research Query",
                value=f"Provide a comprehensive investment analysis of {ticker}, including financial health, growth prospects, valuation assessment, and key risks.",
                height=100,
                help="Describe what you want to research",
            )

        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            if not ticker or not query:
                st.warning("Please enter both a ticker and research query.")
            else:
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()

                phases = [
                    ("🔍 Gathering research data...", 0.15),
                    ("📊 Fetching stock prices & ratios...", 0.30),
                    ("📰 Searching news & filings...", 0.45),
                    ("🧠 Running financial analysis...", 0.60),
                    ("✅ Fact-checking claims...", 0.75),
                    ("📝 Writing research report...", 0.90),
                ]

                # Start animation in a separate display while waiting
                with st.spinner("Running multi-agent research pipeline..."):
                    try:
                        # Show progress animation
                        for phase_text, phase_pct in phases:
                            status_text.write(phase_text)
                            progress_bar.progress(phase_pct)
                            time.sleep(0.5)

                        resp = httpx.post(
                            f"{API_BASE}/research/analyze",
                            json={"query": query, "ticker": ticker},
                            timeout=300,
                        )

                        progress_bar.progress(1.0)
                        status_text.write("✅ Analysis complete!")

                        if resp.status_code == 200:
                            result = resp.json()

                            # Display report
                            st.divider()
                            st.subheader(f"📊 Investment Research Report: {ticker}")

                            # Phases completed
                            phases_completed = result.get("phases_completed", [])
                            cols = st.columns(len(phases_completed))
                            phase_icons = {
                                "research": "🔍",
                                "analysis": "🧠",
                                "fact_check": "✅",
                                "report_generation": "📝",
                            }
                            for col, phase in zip(cols, phases_completed):
                                icon = phase_icons.get(phase, "📌")
                                col.success(f"{icon} {phase.replace('_', ' ').title()}")

                            # Main report
                            st.markdown(result.get("report", "No report generated."))

                            # Errors
                            errors = result.get("errors", [])
                            if errors:
                                with st.expander("⚠️ Data Collection Warnings"):
                                    for err in errors:
                                        st.warning(err)

                            # Citations
                            citations = result.get("citations", [])
                            if citations:
                                with st.expander(
                                    f"📚 Sources & Citations ({len(citations)} sources)"
                                ):
                                    for cite in citations:
                                        st.markdown(
                                            f"**{cite.get('id', '?')}** "
                                            f"[{cite.get('source_type', '').upper()}] "
                                            f"{cite.get('source_name', 'Unknown')}"
                                        )
                                        st.caption(
                                            f"Excerpt: \"{cite.get('excerpt', '')[:150]}...\""
                                        )

                            # Fact-check
                            fc = result.get("fact_check", {})
                            if fc.get("report"):
                                with st.expander("✅ Fact-Check Report"):
                                    st.markdown(fc["report"])

                            # Download report
                            report_text = result.get("report", "")
                            st.download_button(
                                label="📥 Download Report (Markdown)",
                                data=report_text,
                                file_name=f"{ticker}_research_report.md",
                                mime="text/markdown",
                            )

                            # JSON export
                            st.download_button(
                                label="📥 Download Full Data (JSON)",
                                data=json.dumps(result, indent=2),
                                file_name=f"{ticker}_research_data.json",
                                mime="application/json",
                            )

                        else:
                            st.error(f"Analysis failed: {resp.text}")

                    except httpx.TimeoutException:
                        st.error("Request timed out. The analysis may take a few minutes.")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    # Tab 2: Quick Quote
    with tab2:
        st.header("Quick Stock Quote")

        quick_ticker = st.text_input(
            "Enter Ticker", value="MSFT", key="quick_ticker"
        ).upper()

        if st.button("Get Quote", key="quick_quote_btn"):
            with st.spinner(f"Fetching data for {quick_ticker}..."):
                try:
                    resp = httpx.post(
                        f"{API_BASE}/research/quick-quote",
                        params={"ticker": quick_ticker},
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        st.markdown(data.get("data", "No data"))
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # Tab 3: Document Search
    with tab3:
        st.header("Search Financial Documents")
        st.info(
            "Search through ingested annual reports, earnings transcripts, and SEC filings."
        )

        search_query = st.text_input(
            "Search Query",
            placeholder="e.g., revenue growth drivers, risk factors, capital allocation strategy",
            key="doc_search",
        )
        num_results = st.slider("Number of Results", 1, 20, 5, key="num_results")

        if st.button("🔍 Search", key="search_btn"):
            if not search_query:
                st.warning("Please enter a search query.")
            else:
                with st.spinner("Searching documents..."):
                    try:
                        resp = httpx.post(
                            f"{API_BASE}/documents/search",
                            params={
                                "query": search_query,
                                "num_results": num_results,
                            },
                            timeout=30,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            results = data.get("results", [])
                            if not results:
                                st.info("No results found. Try uploading documents first.")
                            else:
                                for i, result in enumerate(results, 1):
                                    with st.expander(
                                        f"Result {i} — "
                                        f"{result['metadata'].get('filename', 'Unknown')} "
                                        f"(Score: {result['score']:.3f})"
                                    ):
                                        st.markdown(f"**Content:**\n{result['content']}")
                                        st.json(result["metadata"])
                        else:
                            st.error(f"Search failed: {resp.text}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()