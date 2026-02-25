## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

# BUG FIX 6: Wrong import path. 'from crewai.agents import Agent' does not exist.
# Correct import:
from crewai import Agent, LLM

from tools import search_tool, FinancialDocumentTool

# BUG FIX 7: 'llm = llm' is a NameError — 'llm' was never defined.
# Load the LLM properly using environment variables.
llm = LLM(
    model=os.getenv("MODEL", "openai/gpt-4o-mini"),
    api_key=os.getenv("OPENAI_API_KEY"),
)

# PROMPT FIX: The original goal and backstory encouraged hallucination, fabricating
# URLs, ignoring the user query, and making up financial facts. Replaced with a
# professional, accurate, and responsible prompt.
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal=(
        "Thoroughly analyze the provided financial document to answer the user's query: {query}. "
        "Extract key financial metrics, trends, and data-driven insights. "
        "Provide accurate, evidence-based analysis grounded solely in the document's content."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are a CFA-certified financial analyst with 15+ years of experience analyzing "
        "corporate financial statements, earnings reports, and investment documents. "
        "You are known for your rigorous, data-driven approach and clear communication. "
        "You always cite specific figures from the document and clearly distinguish between "
        "facts, analysis, and opinion. You adhere to SEC guidelines and never fabricate data."
    ),
    tools=[FinancialDocumentTool.read_data_tool],
    # BUG FIX 8: Parameter was 'tool' (singular) — correct CrewAI param is 'tools' (plural).
    llm=llm,
    max_iter=5,   # BUG FIX 9: max_iter=1 prevents agents from retrying on tool errors.
    max_rpm=10,   # BUG FIX 10: max_rpm=1 causes extreme throttling in production.
    allow_delegation=False  # Only one agent used in crew; delegation would error.
)

# PROMPT FIX: Verifier agent originally approved everything without reading — dangerous.
verifier = Agent(
    role="Financial Document Verifier",
    goal=(
        "Verify that the uploaded file is a legitimate financial document. "
        "Check for standard financial sections such as income statements, balance sheets, "
        "cash flow statements, or financial ratios. Report clearly if the document is not financial."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are a compliance officer with experience in financial document review. "
        "You carefully read documents before making any determination. "
        "You maintain high standards of accuracy and flag documents that don't meet "
        "financial reporting standards."
    ),
    llm=llm,
    max_iter=5,
    max_rpm=10,
    allow_delegation=False
)

# PROMPT FIX: investment_advisor was a fake salesperson recommending meme stocks.
investment_advisor = Agent(
    role="Investment Advisor",
    goal=(
        "Based on the verified financial analysis, provide objective, balanced investment "
        "considerations. Highlight both opportunities and risks supported by the document's data. "
        "Always include appropriate disclaimers that this is not personalized financial advice."
    ),
    verbose=True,
    backstory=(
        "You are a licensed investment advisor with experience across equities, fixed income, "
        "and alternative assets. You provide balanced, research-backed perspectives and always "
        "recommend that clients consult a certified financial planner for personalized advice. "
        "You comply with all SEC and FINRA regulations."
    ),
    llm=llm,
    max_iter=5,
    max_rpm=10,
    allow_delegation=False
)

# PROMPT FIX: risk_assessor was encouraging YOLO investing and ignoring real risk factors.
risk_assessor = Agent(
    role="Risk Assessment Specialist",
    goal=(
        "Perform a structured risk assessment of the financial document, identifying "
        "quantitative and qualitative risk factors such as leverage ratios, liquidity risk, "
        "market exposure, and operational risks. Provide a balanced view of risk levels."
    ),
    verbose=True,
    backstory=(
        "You are a risk management professional with a background in quantitative finance. "
        "You use established frameworks such as VaR, stress testing, and ratio analysis "
        "to objectively assess risk. You provide nuanced risk ratings backed by data, "
        "and you understand that risk tolerance varies by investor profile."
    ),
    llm=llm,
    max_iter=5,
    max_rpm=10,
    allow_delegation=False
)
