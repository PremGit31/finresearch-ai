# scripts/seed_sample_data.py
"""
Seed sample financial data for demo purposes.
Creates sample earnings transcripts and financial summaries.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import RAW_DIR


SAMPLE_TRANSCRIPT = """
APPLE INC. (AAPL) Q4 2024 EARNINGS CALL TRANSCRIPT

PARTICIPANTS:
- Tim Cook, CEO
- Luca Maestri, CFO
- Analysts from major investment banks

TIM COOK, CEO:
Thank you for joining us today. We are thrilled to report record fourth quarter results. 
Revenue came in at $94.9 billion, up 6% year over year. This was a September quarter record 
and we set all-time revenue records in several countries and regions.

iPhone revenue was $46.2 billion, up 6% year over year, and set a September quarter record 
driven by the strong performance of the iPhone 16 lineup. We saw particularly strong demand 
for the Pro models.

Services revenue reached a new all-time record of $25.0 billion, up 12% year over year. 
This continues the incredible growth trajectory of our services business, which now has over 
1 billion paid subscriptions.

Mac revenue was $7.7 billion, up 2% year over year, driven by the new MacBook Pro with M4 chips.

iPad revenue was $6.9 billion, down 1% year over year.

Wearables, Home and Accessories revenue was $9.0 billion, relatively flat year over year.

LUCA MAESTRI, CFO:
Our gross margin was 46.2%, up 40 basis points year over year, driven by the favorable 
mix toward services revenue which carries higher margins.

Operating expenses were $14.3 billion, reflecting our continued investment in innovation 
while maintaining discipline.

Net income for the quarter was $24.7 billion, or $1.64 per diluted share, a new September 
quarter record.

We generated operating cash flow of $26.8 billion and returned over $29 billion to shareholders 
through dividends and share repurchases.

Our total cash and marketable securities position was $153 billion at quarter end, with 
net cash of approximately $50 billion.

RISK FACTORS DISCUSSED:
- Regulatory challenges in the EU regarding the Digital Markets Act
- Potential tariff impacts on supply chain
- Increasing competition in the smartphone market, particularly in China
- Currency headwinds from strong US dollar
- AI investment requirements to remain competitive

GROWTH CATALYSTS:
- Apple Intelligence (AI features) driving upgrade cycles
- Services ecosystem growth and monetization
- Expansion in India and emerging markets
- Vision Pro spatial computing platform
- New health and fitness capabilities

GUIDANCE:
For Q1 2025, we expect revenue growth in the low-to-mid single digits year over year, 
with gross margin between 46% and 47%.
"""

SAMPLE_ANNUAL_REPORT = """
MICROSOFT CORPORATION
ANNUAL REPORT 2024 (FISCAL YEAR ENDING JUNE 2024)

ITEM 1: BUSINESS OVERVIEW

Microsoft Corporation is a technology company whose mission is to empower every person 
and organization on the planet to achieve more. We develop, license, and support a range 
of software products, services, and devices.

Our segments include:
1. Productivity and Business Processes ($77.4 billion revenue, +13% YoY)
   - Microsoft 365, LinkedIn, Dynamics 365
2. Intelligent Cloud ($96.8 billion revenue, +21% YoY)
   - Azure, SQL Server, GitHub, Nuance
3. More Personal Computing ($59.7 billion revenue, +2% YoY)
   - Windows, Devices, Gaming, Search advertising

ITEM 7: MANAGEMENT DISCUSSION AND ANALYSIS

FINANCIAL HIGHLIGHTS:
- Total Revenue: $236.6 billion (+16% YoY)
- Operating Income: $109.4 billion (+24% YoY)
- Net Income: $88.1 billion (+22% YoY)
- Diluted EPS: $11.80 (+22% YoY)
- Operating Cash Flow: $118.5 billion (+26% YoY)
- Free Cash Flow: $74.1 billion (+25% YoY)

Azure and other cloud services revenue grew 30% year over year, driven by strong demand 
for AI workloads. Over 65% of the Fortune 500 use Azure OpenAI Service.

CAPITAL ALLOCATION:
- Capital expenditures: $44.5 billion (primarily for cloud and AI infrastructure)
- Share repurchases: $17.6 billion
- Dividends paid: $22.3 billion
- Total shareholder returns: $39.9 billion

RISK FACTORS:
- Intense competition in cloud computing from AWS and Google Cloud
- Regulatory scrutiny of AI products and data practices
- Cybersecurity threats and incidents
- Integration of Activision Blizzard ($68.7 billion acquisition)
- Dependence on continued growth of cloud adoption

BALANCE SHEET:
- Total Assets: $512.1 billion
- Total Cash: $75.5 billion
- Long-term Debt: $42.7 billion
- Stockholders' Equity: $268.5 billion

VALUATION METRICS:
- P/E Ratio: ~35x trailing earnings
- EV/EBITDA: ~25x
- Price/Free Cash Flow: ~40x
- Dividend Yield: ~0.7%
"""


def seed_sample_data():
    """Create sample financial documents for demo."""
    # Create sample files
    transcript_path = RAW_DIR / "AAPL_Q4_2024_Earnings_Transcript.txt"
    annual_report_path = RAW_DIR / "MSFT_Annual_Report_2024.txt"

    transcript_path.write_text(SAMPLE_TRANSCRIPT)
    print(f"✅ Created: {transcript_path}")

    annual_report_path.write_text(SAMPLE_ANNUAL_REPORT)
    print(f"✅ Created: {annual_report_path}")

    print("\n📄 Sample data created. Run 'python scripts/ingest_documents.py' to index them.")


if __name__ == "__main__":
    seed_sample_data()