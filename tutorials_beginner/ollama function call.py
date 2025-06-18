import autogen
from autogen.cache import Cache

from finrobot.utils import get_current_date, register_keys_from_json
from finrobot.data_source import FinnHubUtils, YFinanceUtils
from autogen import AssistantAgent, UserProxyAgent

from typing import Annotated

config_list = [
    {
        "model": "llama3.2:latest",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
    }
]

llm_config = {"config_list": config_list, "timeout": 120, "temperature": 0}

register_keys_from_json("/root/finrobot/config_api_keys")

analyst = AssistantAgent(
    name="Market_Analyst",
    llm_config=llm_config,
)

user_proxy = UserProxyAgent("user_proxy", code_execution_config=False, max_consecutive_auto_reply=1,  is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in x.get("content", ""),
    human_input_mode="NEVER")

from finrobot.toolkits import register_toolkits
tools = [
    {
        "function": YFinanceUtils.get_stock_data,
        #"function": FinnHubUtils.get_company_news,
        "name": "get_stock_news",
        "description": "retrieve stock information related to designated company"
    }
]
register_toolkits(tools, analyst, user_proxy)

company = "apple"
date='2025-01-01'

user_proxy.initiate_chat(analyst, message=f"What is stock price available for {company} from {date} upon {get_current_date()}.")

