## Importing libraries and files
from crewai import Task

from agents import financial_analyst, verifier
from tools import search_tool, FinancialDocumentTool

# PROMPT FIX: Task descriptions originally told agents to ignore the user query,
# make up URLs, hallucinate data, and contradict themselves.
# All tasks now have clear, professional descriptions and expected outputs.

# BUG FIX 11: This task was named 'analyze_financial_document' which collides with
# the FastAPI endpoint function of the same name in main.py. Renamed to 'analysis_task'.
analysis_task = Task(
    description=(
        "Read the financial document located at the file path provided in the context. "
        "Answer the user's query: {query}\n\n"
        "Your analysis must:\n"
        "1. Extract and summarize key financial metrics (revenue, profit, margins, cash flow, debt, etc.)\n"
        "2. Identify significant trends (YoY or QoQ changes)\n"
        "3. Highlight key risks mentioned or implied in the document\n"
        "4. Provide data-driven investment considerations\n"
        "5. Cite specific figures and sections from the document to support all claims\n\n"
        "Do NOT fabricate data, URLs, or statistics not present in the document."
    ),
    expected_output=(
        "A structured financial analysis report containing:\n"
        "- Executive Summary (2-3 sentences)\n"
        "- Key Financial Metrics with actual numbers from the document\n"
        "- Trend Analysis with percentage changes where available\n"
        "- Risk Factors identified from the document\n"
        "- Investment Considerations (clearly labeled as general observations, not personalized advice)\n"
        "- Disclaimer: 'This analysis is for informational purposes only and does not constitute "
        "personalized financial advice. Consult a licensed financial advisor before making investment decisions.'"
    ),
    agent=financial_analyst,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False,
)

investment_analysis_task = Task(
    description=(
        "Based on the financial data extracted from the document, provide an objective "
        "investment analysis in response to: {query}\n\n"
        "Focus on:\n"
        "1. Valuation indicators (P/E, P/B, EV/EBITDA if available)\n"
        "2. Growth trajectory based on reported figures\n"
        "3. Competitive positioning mentioned in the document\n"
        "4. Capital allocation strategy (dividends, buybacks, capex)\n"
        "5. Management guidance or outlook if provided\n\n"
        "Only use data present in the document. Do not fabricate financial ratios or comparisons."
    ),
    expected_output=(
        "An investment analysis including:\n"
        "- Valuation Summary with document-sourced metrics\n"
        "- Growth Analysis based on reported figures\n"
        "- Strengths and Concerns from the document\n"
        "- Balanced investment considerations (bull and bear case)\n"
        "- Appropriate disclaimer about not constituting personalized advice"
    ),
    agent=financial_analyst,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False,
)

risk_assessment_task = Task(
    description=(
        "Perform a structured risk assessment of the financial document in context of: {query}\n\n"
        "Evaluate:\n"
        "1. Liquidity risk (current ratio, quick ratio, cash position)\n"
        "2. Leverage risk (debt-to-equity, interest coverage)\n"
        "3. Market/revenue risk (revenue concentration, geographic exposure)\n"
        "4. Operational risks mentioned in management discussion\n"
        "5. Regulatory or legal risks disclosed\n\n"
        "Base all risk ratings on actual data from the document."
    ),
    expected_output=(
        "A risk assessment report with:\n"
        "- Overall Risk Rating (Low/Medium/High) with justification\n"
        "- Liquidity Risk analysis with supporting figures\n"
        "- Leverage Risk analysis with supporting figures\n"
        "- Key Risk Factors (minimum 3, maximum 8, all document-sourced)\n"
        "- Risk Mitigation factors mentioned in the document\n"
        "- Note: Risk assessments are general and should be combined with professional advice"
    ),
    agent=financial_analyst,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False,
)

verification_task = Task(
    description=(
        "Verify whether the uploaded document is a legitimate financial document.\n\n"
        "Check for the presence of:\n"
        "1. Standard financial statements (income statement, balance sheet, cash flow)\n"
        "2. Financial figures (revenue, expenses, assets, liabilities)\n"
        "3. Time periods or reporting periods\n"
        "4. Company identification information\n\n"
        "Read the document carefully before making any determination."
    ),
    expected_output=(
        "A verification report stating:\n"
        "- Document Type (e.g., Annual Report, Earnings Release, 10-K, etc.)\n"
        "- Is Financial Document: Yes/No with clear reasoning\n"
        "- Key Sections Identified\n"
        "- Company Name and Reporting Period (if found)\n"
        "- Any concerns about document completeness or authenticity"
    ),
    agent=financial_analyst,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False
)
