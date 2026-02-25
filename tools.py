## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

# BUG FIX 1: Wrong import - 'from crewai_tools import tools' is not valid.
# Correct import for SerperDevTool:
from crewai_tools import SerperDevTool

# BUG FIX 2: Pdf/PDFMinerLoader was never imported. Using langchain's PyPDFLoader.
from langchain_community.document_loaders import PyPDFLoader

from crewai.tools import tool

## Creating search tool
search_tool = SerperDevTool()

## Creating custom pdf reader tool
class FinancialDocumentTool():

    # BUG FIX 3: 'async def' makes this a coroutine — CrewAI tools must be synchronous.
    # BUG FIX 4: Missing @staticmethod decorator (method has no 'self' param).
    # BUG FIX 5: 'Pdf' class was never imported/defined — replaced with PyPDFLoader.
    @staticmethod
    @tool("Financial Document Reader")
    def read_data_tool(path: str = 'data/sample.pdf') -> str:
        """Tool to read data from a PDF file.

        Args:
            path (str): Path of the PDF file. Defaults to 'data/sample.pdf'.

        Returns:
            str: Full text content of the financial document.
        """
        loader = PyPDFLoader(file_path=path)
        docs = loader.load()

        full_report = ""
        for data in docs:
            content = data.page_content

            # Remove extra whitespaces
            while "\n\n" in content:
                content = content.replace("\n\n", "\n")

            full_report += content + "\n"

        return full_report


## Creating Investment Analysis Tool
class InvestmentTool:
    @staticmethod
    @tool("Investment Analyzer")
    def analyze_investment_tool(financial_document_data: str) -> str:
        """Analyze investment opportunities from financial document data.

        Args:
            financial_document_data (str): Raw text from a financial document.

        Returns:
            str: Processed financial data ready for investment analysis.
        """
        processed_data = financial_document_data

        # Clean up double spaces
        i = 0
        while i < len(processed_data):
            if processed_data[i:i+2] == "  ":
                processed_data = processed_data[:i] + processed_data[i+1:]
            else:
                i += 1

        return processed_data


## Creating Risk Assessment Tool
class RiskTool:
    @staticmethod
    @tool("Risk Assessment Tool")
    def create_risk_assessment_tool(financial_document_data: str) -> str:
        """Assess financial risk from document data.

        Args:
            financial_document_data (str): Raw text from a financial document.

        Returns:
            str: Processed data for risk assessment.
        """
        return financial_document_data
