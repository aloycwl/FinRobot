import os

os.chdir("openbb-agent")

from agent.dspy_obb_agent import DSPYOpenBBAgent
from dotenv import load_dotenv,find_dotenv
from agent.database import load_database, build_database, build_docs_metadata
from agent.dspy_agent import OpenBBAgentChroma
import os 

load_dotenv(find_dotenv(),override=True)

from agent.database import build_graph

router_names_graph,router_names = build_graph()

from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.pyplot as plt
import networkx as nx

for router in router_names:
    graph = router_names_graph[router]
    pos = graphviz_layout(graph, prog="dot")
    plt.figure(figsize=(20, 10))
    nx.draw(graph, pos, with_labels=True, node_size=500, node_color="skyblue", font_size=5, font_weight="bold", arrows=True)
    plt.title(f"{router.upper()}")
    plt.show()

openbb_collection = load_database(os.environ['OPENAI_API_KEY'])
obb_chroma = OpenBBAgentChroma(openbb_collection) 
dspy_obb = DSPYOpenBBAgent(obb_chroma)

from openbb import obb
# Login to OpenBB and prefer dataframe outputs
obb.account.login(pat=os.environ['OBB_PAT'])

obb.user.preferences.output_type = "dataframe"

output = dspy_obb("Is tesla overvalued?")

print(output)

# Pass provider lists form OpenBB
PROVIDER_LIST = []

from typing import Optional
def function_calling_openbb(question:str)->Optional[str]:
    """This tool can be used to get financial data from the popular open-source platform OpenBB. 
       It takes a question and returns data by calling functions from OpenBB. OpenBB offers access to equity, options, crypto, forex, macro economy, fixed income, 
       and more while also offering a broad range of extensions to enhance the user experience according to their needs.

    Args:
        question (str): question to get information

    Returns:
        Optional[str]: It returns the data in markdown tables or None if no data is available
    """

    output = dspy_obb(question=question,provider_list=PROVIDER_LIST)
    return output

from autogen import ConversableAgent
from autogen import register_function


llm_config = {"model":"gpt-4-turbo"}

system_message = "You have to respond to the question by building a plan first and then breakdown the plan into subquestions and use the function_calling_openbb tool to get financial data.\n" + \
                    "Make sure that you have plan well and ask relevant questions to the function_calling_openbb tool to get financial data. Also, restrict your question to one financial entity (like ticker) at one time.\n" + \
                    "For instance, if the user queries about the stock price quote of Apple and Microsoft, make sure to breakdown the it into subquestions stock price quote of Apple and stock price quote of Microsoft."


user_proxy = ConversableAgent(
    name = "Planner Admin",
    system_message=system_message,
    code_execution_config=False,
    llm_config=llm_config,
    human_input_mode="NEVER",
    is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
)

tool_proxy = ConversableAgent(
  name="Tool Proxy",
  llm_config={"model":"gpt-3.5-turbo"},
  system_message="Check if the Planner Admin is querying the OpenBB tool properly, and provide feedback if necessary. Answer TERMINATE after you are done.",
  is_termination_msg=lambda msg: "exit" in msg.get("content",""),
  default_auto_reply="Use the function_calling_openbb tool to answer the question",
  human_input_mode="NEVER",
  )

register_function(
    function_calling_openbb,
    caller=user_proxy,
    executor=tool_proxy,
    name = "function_calling_openbb",
    description="Tool to query OpenBB documentation to get financial data."
)

input_text = "What is the price consensus of Google and Microsoft? Compare and contrast between them"

chat_result = user_proxy.initiate_chat(
        recipient=tool_proxy,
        message=input_text,
        max_turns=5
    )

input_text = "What is the price consensus of Google and Microsoft? Compare and contrast between them"

chat_result = user_proxy.initiate_chat(
        recipient=tool_proxy,
        message=input_text,
        max_turns=5
    )

input_text = "How is the Gold futures market doing? Compare and contrast between Gold and Bitcoin?"

chat_result = user_proxy.initiate_chat(
        recipient=tool_proxy,
        message=input_text,
        max_turns=5
    )

