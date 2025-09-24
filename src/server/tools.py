import os
from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults


@tool
def add(a: int, b: int):
    """Add two numbers. Please let the user know that you're adding the numbers BEFORE you call the tool"""
    return a + b


# Read Tavily API key from environment
tavily_api_key = os.getenv("TAVILY_API_KEY")

# Initialize Tavily tool only if API key exists
if tavily_api_key:
    tavily_tool = TavilySearchResults(
        tavily_api_key=tavily_api_key,  # pass key explicitly
        max_results=5,
        include_answer=True,
        description=(
            "This is a search tool for accessing the internet.\n\n"
            "Let the user know you're asking your friend Tavily for help before you call the tool."
        ),
    )
    TOOLS = [add, tavily_tool]
else:
    # Fallback: Tavily disabled if no API key
    TOOLS = [add]

