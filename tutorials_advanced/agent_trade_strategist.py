import os
import autogen
from autogen.cache import Cache

from finrobot.functional.quantitative import BackTraderUtils
from finrobot.functional.coding import IPythonUtils
from finrobot.toolkits import register_toolkits, register_code_writing
from textwrap import dedent

config_list = autogen.config_list_from_json(
    "../OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4-0125-preview"],
    },
)
llm_config = {
    "config_list": config_list,
    "timeout": 120,
    # "temperature": 0 # for debug convenience
    "temperature": 0.5
}

from finrobot.functional.coding import default_path

# Intermediate strategy modules will be saved in this directory
work_dir = default_path
os.makedirs(work_dir, exist_ok=True)

strategist = autogen.AssistantAgent(
    name="Trade_Strategist",
    system_message=dedent(f"""
        You are a trading strategist known for your expertise in developing sophisticated trading algorithms. 
        Your task is to leverage your coding skills to create a customized trading strategy using the BackTrader Python library, and save it as a Python module. 
        Remember to log necessary information in the strategy so that further analysis could be done.
        You can also write custom sizer / indicator and save them as modules, which would allow you to generate more sophisticated strategies.
        After creating the strategy, you may backtest it with the tool you're provided to evaluate its performance and make any necessary adjustments.
        All files you created during coding will automatically be in `{work_dir}`, no need to specify the prefix. 
        But when calling the backtest function, module path should be like `{work_dir.strip('/')}.<module_path>` and savefig path should consider `{work_dir}` as well.
        Reply TERMINATE to executer when the strategy is ready to be tested.
        """),
    llm_config=llm_config,
    
)
user_proxy = autogen.UserProxyAgent(
    name="User_Proxy",
    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").endswith("TERMINATE"),
    human_input_mode="NEVER", # change this to "ALWAYS" if you want to manually interact with the strategist
    # max_consecutive_auto_reply=10,
    code_execution_config={
        "last_n_messages": 1,
        "work_dir": work_dir,
        "use_docker": False,
    }
)
register_code_writing(strategist, user_proxy)
register_toolkits([BackTraderUtils.back_test, IPythonUtils.display_image], strategist, user_proxy)

company = "Microsoft"
start_date = "2022-01-01"
end_date = "2024-01-01"

task = dedent(f"""
    Based on {company}'s stock data from {start_date} to {end_date}, develop a trading strategy that would performs well on this stock.
    Write your own custom indicator/sizer if needed. Other backtest settings like initial cash are all up to you to decide.
    After each backtest, display the saved backtest result chart, then report the current situation and your thoughts towards optimization.
    Modify the code to optimize your strategy or try more different indicators / sizers into account for better performance.
    Your strategy should at least outperform the benchmark strategy of buying and holding the stock.
""")

with Cache.disk() as cache:
    user_proxy.initiate_chat(
        recipient=strategist,
        message=task,
        max_turns=30,
        summary_method="last_msg"
    )

