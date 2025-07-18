from langchain.agents import Tool, initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
def run_workflow_planner(task: str):
    search = DuckDuckGoSearchRun()
    tools = [
        Tool(
            name="DuckDuckGo Search",
            func=search.run,
            description="Useful for answering questions about current events or research",
        )
    ]

    llm = ChatOpenAI(
        temperature=0,
        model=os.getenv("MODEL_1"),  # or any OpenRouter-compatible model
        base_url=os.getenv("URL"),
        api_key=os.getenv("API_KEY"),
    )

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False
    )

    return agent.run(task)
