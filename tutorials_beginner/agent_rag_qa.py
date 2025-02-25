import autogen
from finrobot.agents.workflow import SingleAssistantRAG

# Read OpenAI API keys from a JSON file
llm_config = {
    "config_list": autogen.config_list_from_json(
        "../OAI_CONFIG_LIST",
        filter_dict={"model": ["gpt-4-0125-preview"]},
    ),
    "timeout": 120,
    "temperature": 0,
}

assitant = SingleAssistantRAG(
    "Data_Analyst",
    llm_config,
    human_input_mode="NEVER",
    retrieve_config={
        "task": "qa",
        "vector_db": None,  # Autogen has bug for this version
        "docs_path": [
            "../report/Microsoft_Annual_Report_2023.pdf",
        ],
        "chunk_token_size": 1000,
        "get_or_create": True,
        "collection_name": "msft_analysis",
        "must_break_at_empty_line": False,
    },
)
assitant.chat("How's msft's 2023 income? Provide with some analysis.")

assitant = SingleAssistantRAG(
    "Data_Analyst",
    llm_config,
    human_input_mode="NEVER",
    retrieve_config={
        "task": "qa",
        "vector_db": None,  # Autogen has bug for this version
        "docs_path": [
            "../report/2023-07-27_10-K_msft-20230630.htm.pdf",
        ],
        "chunk_token_size": 2000,
        "collection_name": "msft_10k",
        "get_or_create": True,
        "must_break_at_empty_line": False,
    },
    rag_description="Retrieve content from MSFT's 2023 10-K report for detailed question answering.",
)
assitant.chat("How's msft's 2023 income? Provide with some analysis.")

