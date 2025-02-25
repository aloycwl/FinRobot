
import os
import autogen
from autogen import AssistantAgent, UserProxyAgent
from autogen.agentchat.contrib.multimodal_conversable_agent import MultimodalConversableAgent
from autogen.cache import Cache

from finrobot.utils import get_current_date, register_keys_from_json
from finrobot.data_source.finnhub_utils import FinnHubUtils
from finrobot.functional.charting import MplFinanceUtils

from textwrap import dedent
from matplotlib import pyplot as plt
from PIL import Image

config_list_4v = autogen.config_list_from_json(
    "/root/FinRobot/OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4-1106-vision-preview"],
    },
)
config_list_gpt4 = autogen.config_list_from_json(
    "/root/FinRobot/OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4-0125-preview"],
    },
)

# Register FINNHUB API keys for later use
register_keys_from_json("/root/FinRobot/config_api_keys")

# Intermediate results/charts will be saved in this directory
working_dir = "/root/FinRobot/coding"
os.makedirs(working_dir, exist_ok=True)

market_analyst = MultimodalConversableAgent(
    name="Market_Analyst",
    max_consecutive_auto_reply=10,
    llm_config={"config_list": config_list_4v, "temperature": 0},
    system_message=dedent("""
        Your are a Market Analyst. Your task is to analyze the financial data and market news.
        Reply "TERMINATE" in the end when everything is done.
        """)
)
data_provider = AssistantAgent(
    name="Data_Provider",
    llm_config={"config_list": config_list_gpt4, "temperature": 0},
    system_message=dedent("""
        You are a Data Provider. Your task is to provide charts and necessary market information.
        Use the functions you have been provided with.
        Reply "TERMINATE" in the end when everything is done.
        """)
)
user_proxy = UserProxyAgent(
    name="User_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: x.get("content", "") and x.get(
        "content", "").endswith("TERMINATE"),
    code_execution_config={
        "work_dir": working_dir,
        "use_docker": False
    },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
)

from finrobot.toolkits import register_toolkits

tools = [
    {
        "function": FinnHubUtils.get_company_news,
        "name": "get_company_news",
        "description": "retrieve market news related to designated company"
    },
    {
        "function": MplFinanceUtils.plot_stock_price_chart,
        "name": "plot_stock_price_chart",
        "description": "plot stock price chart of designated company"
    }
]
register_toolkits(tools, data_provider, user_proxy)

company = "Tesla"
# company = "APPLE"

with Cache.disk() as cache:  # image cannot be cached
    autogen.initiate_chats(
        [
            {
                "sender": user_proxy,
                "recipient": data_provider,
                "message": dedent(f"""
                Gather information available upon {get_current_date()} for {company}, 
                including its recent market news and a candlestick chart of the stock 
                price trend. Save the chart in `{working_dir}/result.jpg`
                """),           # As currently AutoGen has the bug of not respecting `work_dir` when using function call, we have to specify the directory
                "clear_history": True,
                "silent": False,
                "summary_method": "last_msg",
            },
            {
                "sender": user_proxy,
                "recipient": market_analyst,
                "message": dedent(f"""
                With the stock price chart provided, along with recent market news of {company}, 
                analyze the recent fluctuations of the stock and the potential relationship with 
                market news. Provide your predictive analysis for the stock's trend in the coming 
                week. Reply TERMINATE when the task is done.
                """),
                "max_turns": 1,  # max number of turns for the conversation
                "summary_method": "last_msg",
                # cheated here for stability
                "carryover": f"<img {working_dir}/result.jpg>"
            }
        ]
    )

img = Image.open(f"{working_dir}/result.jpg")
plt.imshow(img)
plt.axis("off")  # Hide the axes
plt.show()

