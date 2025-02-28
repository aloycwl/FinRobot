import autogen
from autogen import AssistantAgent, UserProxyAgent
from autogen.agentchat.contrib.multimodal_conversable_agent import MultimodalConversableAgent
from autogen.cache import Cache
from textwrap import dedent

config_list_4v = autogen.config_list_from_json(
    "/root/finrobot/OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4-1106-vision-preview"],
    },
)
config_list = autogen.config_list_from_json(
    "/root/finrobot/OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4-0125-preview"],
    },
)
llm_config_4v = {"config_list": config_list_4v, "temperature": 0.0}
llm_config = {"config_list": config_list, "temperature": 0.0}

from finrobot.toolkits import register_toolkits
from finrobot.functional.charting import MplFinanceUtils
from finrobot.functional.quantitative import BackTraderUtils
from finrobot.functional.coding import IPythonUtils


strategist = MultimodalConversableAgent(
    name="Trade_Strategist",
    system_message=dedent(
        """
        You are a trading strategist who inspect financial charts and optimize trading strategies.
        You have been tasked with developing a Simple Moving Average (SMA) Crossover strategy.
        You have the following main actions to take:
        1. Ask the backtesting analyst to plot historical stock price data with designated ma parameters.
        2. Inspect the stock price chart and determine fast/slow parameters.
        3. Ask the backtesting analyst to backtest the SMACrossover trading strategy with designated parameters to evaluate its performance. 
        4. Inspect the backtest result and optimize the fast/slow parameters based on the returned results.
        Reply TERMINATE when you think the strategy is good enough.
        """
    ),
    llm_config=llm_config_4v,
)

analyst = AssistantAgent(
    name="Backtesting_Analyst",
    system_message=dedent(
        """
        You are a backtesting analyst with a strong command of quantitative analysis tools. 
        You have two main tasks to perform, choose one each time you are asked by the trading strategist:
        1. Plot historical stock price data with designated ma parameters according to the trading strategist's need.
        2. Backtest the SMACross trading strategy with designated parameters and save the results as image file.
        For both tasks, after the tool calling, you should do as follows:
            1. display the created & saved image file using the `display_image` tool;
            2. Assume the saved image file is "test.png", reply as follows: "Optimize the fast/slow parameters based on this image <img test.png>. TERMINATE".
        """
    ),
    llm_config=llm_config,
)
analyst_executor = UserProxyAgent(
    name="Backtesting_Analyst_Executor",
    human_input_mode="NEVER",
    is_termination_msg=lambda x: x.get("content", "")
    and x.get("content", "").find("TERMINATE") >= 0,
    code_execution_config={
        "last_n_messages": 1,
        "work_dir": "coding",
        "use_docker": False,
    },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
)
register_toolkits(
    [
        BackTraderUtils.back_test,
        MplFinanceUtils.plot_stock_price_chart,
        IPythonUtils.display_image,
    ],
    analyst,
    analyst_executor,
)

def reflection_message_analyst(recipient, messages, sender, config):
    print("Reflecting strategist's response ...")
    last_msg = recipient.chat_messages_for_summary(sender)[-1]["content"]
    return (
        "Message from Trade Strategist is as follows:"
        + last_msg
        + "\n\nBased on his information, conduct a backtest on the specified stock and strategy, and report your backtesting results back to the strategist."
    )


user_proxy = UserProxyAgent(
    name="User_Proxy",
    is_termination_msg=lambda x: x.get("content", "")
    and x.get("content", "").endswith("TERMINATE"),
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config={
        "last_n_messages": 1,
        "work_dir": "coding",
        "use_docker": False,
    },  # User Proxy dont need to execute code here
)

user_proxy.register_nested_chats(
    [
        {
            "sender": analyst_executor,
            "recipient": analyst,
            "message": reflection_message_analyst,
            "max_turns": 10,
            "summary_method": "last_msg",
        }
    ],
    trigger=strategist,
)

company = "Microsoft"
start_date = "2022-01-01"
end_date = "2024-01-01"

task = dedent(
    f"""
    Based on {company}'s stock data from {start_date} to {end_date}, determine the possible optimal parameters for an SMACrossover Strategy over this period. 
    First, ask the analyst to plot a candlestick chart of the stock price data to visually inspect the price movements and make an initial assessment.
    Then, ask the analyst to backtest the strategy parameters using the backtesting tool, and report results back for further optimization.
"""
)

with Cache.disk() as cache:
    user_proxy.initiate_chat(
        recipient=strategist, message=task, max_turns=5, summary_method="last_msg"
    )

