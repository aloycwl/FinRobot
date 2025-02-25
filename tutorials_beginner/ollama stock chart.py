from autogen import AssistantAgent, UserProxyAgent

config_list = [
    {
        "model": "llama3.2:latest",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
    }
]

assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})

user_proxy = UserProxyAgent("user_proxy", code_execution_config={"work_dir": "../result code plot", "use_docker": False})

year=2023
company="apple"

user_proxy.initiate_chat(assistant, message=f"Plot a chart of {company} stock price change in {year} and save in a file. Get information using yfinance.")