import os

os.chdir("/root/FinRobot/tutorials_beginner/finance_llm_data")

ticker = 'GOOG'
year = '2023'
filing_types = ['10-K','10-Q']
include_amends = True

earnings_docs, earnings_call_quarter_vals, speakers_list_1, speakers_list_2, speakers_list_3, speakers_list_4 = get_data(
    ticker=ticker, year=year,data_source='earnings_calls'
)

sec_data,sec_form_names = get_data(
    ticker=ticker, year=year,data_source='unstructured',include_amends=True,filing_types=filing_types
)

print(sec_data[0].page_content[:1000])

print(sec_data[0].metadata)

get_data(ticker=ticker,year=year,data_source='marker_pdf',batch_processing=False,batch_multiplier=1)

# from IPython.display import IFrame
# IFrame("output/SEC_EDGAR_FILINGS/GOOG-2023/goog-20230331-10-Q1.pdf", width=600, height=300)

from IPython.display import display, Markdown
with open('output/SEC_EDGAR_FILINGS_MD/GOOG-2023/goog-20230331-10-Q1/goog-20230331-10-Q1.md', 'r') as file:
    content = file.read()

display(Markdown(content[:10000]))

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings

emb_fn = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
# Or you can use OpenAI embeddings
# from langchain_community.embeddings.openai import OpenAIEmbeddings
# emb_fn = OpenAIEmbeddings(model="text-embedding-3-small",api_key=os.environ['OPENAI_API_KEY'])
text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=100,
        length_function=len,
        # is_separator_regex = False,
    )

earnings_calls_split_docs = text_splitter.split_documents(earnings_docs)

earnings_call_db = Chroma.from_documents(earnings_calls_split_docs, emb_fn, persist_directory="./earnings-call-db",collection_name="earnings_call")

sec_filings_split_docs = text_splitter.split_documents(sec_data)
sec_filings_unstructured_db = Chroma.from_documents(sec_filings_split_docs, emb_fn, persist_directory="./sec-filings-db",collection_name="sec_filings")

from langchain_text_splitters import MarkdownHeaderTextSplitter

headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]
markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

from langchain.schema import Document
markdown_dir = "output/SEC_EDGAR_FILINGS_MD"
md_content_list = []
for md_dirs in os.listdir(os.path.join(markdown_dir,f"{ticker}-{year}")):
  md_file_path = os.path.join(markdown_dir,f"{ticker}-{year}",md_dirs,f"{md_dirs}.md")
  with open(md_file_path, 'r') as file:
    content = file.read()
  md_content_list.append([content,'-'.join(md_dirs.split('-')[-2:])])

sec_markdown_docs = []

for md_content in md_content_list:
  md_header_splits = markdown_splitter.split_text(md_content[0])
  for md_header_docs in md_header_splits:
    # Add a extra metadata of filing type
    md_header_docs.metadata.update({"filing_type":md_content[1]})
  sec_markdown_docs.extend(md_header_splits)

sec_markdown_docs[0]

sec_filings_md_db = Chroma.from_documents(sec_markdown_docs, emb_fn, persist_directory="./sec-filings-md-db",collection_name="sec_filings_md")

quarter_speaker_dict = {
        "Q1":speakers_list_1,
        "Q2":speakers_list_2,
        "Q3":speakers_list_3,
        "Q4":speakers_list_4
    }

def query_database_earnings_call(
        question: str,
        quarter: str
    )->str:
        """This tool will query the earnings call transcripts database for a given question and quarter and it will retrieve
        the relevant text along from the earnings call and the speaker who addressed the relevant documents. This tool helps in answering questions
        from the earnings call transcripts.

        Args:
            question (str): _description_. Question to query the database for relevant documents.
            quarter (str): _description_. the financial quarter that is discussed in the question and possible options are Q1, Q2, Q3, Q4

        Returns:
            str: relevant text along from the earnings call and the speaker who addressed the relevant documents
        """
        assert quarter in earnings_call_quarter_vals, "The quarter should be from Q1, Q2, Q3, Q4"

        req_speaker_list = []
        quarter_speaker_list = quarter_speaker_dict[quarter]

        for sl in quarter_speaker_list:
            if sl in question or sl.lower() in question:
                req_speaker_list.append(sl)
        if len(req_speaker_list) == 0:
            req_speaker_list = quarter_speaker_list

        relevant_docs = earnings_call_db.similarity_search(
            question,
            k=5,
            filter={
                "$and":[
                    {
                        "quarter":{"$eq":quarter}
                    },
                    {
                        "speaker":{"$in":req_speaker_list}
                    }
                ]
            }
        )

        speaker_releavnt_dict = {}
        for doc in relevant_docs:
            speaker = doc.metadata['speaker']
            speaker_text = doc.page_content
            if speaker not in speaker_releavnt_dict:
                speaker_releavnt_dict[speaker] = speaker_text
            else:
                speaker_releavnt_dict[speaker] += " "+speaker_text

        relevant_speaker_text = ""
        for speaker, text in speaker_releavnt_dict.items():
            relevant_speaker_text += speaker + ": "
            relevant_speaker_text += text + "\n\n"

        return relevant_speaker_text

def query_database_unstructured_sec(
            question: str,
            sec_form_name: str
    )->str:
  assert sec_form_name in sec_form_names, f'The search form type should be in {sec_form_names}'

  relevant_docs = sec_filings_unstructured_db.similarity_search(
      question,
      k=5,
      filter={
          "form_name":{"$eq":sec_form_name}
      }
  )
  relevant_section_dict = {}
  for doc in relevant_docs:
      section = doc.metadata['section_name']
      section_text = doc.page_content
      if section not in relevant_section_dict:
          relevant_section_dict[section] = section_text
      else:
          relevant_section_dict[section] += " "+section_text

  relevant_section_text = ""
  for section, text in relevant_section_dict.items():
      relevant_section_text += section + ": "
      relevant_section_text += text + "\n\n"
  return relevant_section_text
     

def query_database_markdown_sec(
            question: str,
            sec_form_name: str
    )->str:
  assert sec_form_name in sec_form_names, f'The search form type should be in {sec_form_names}'

  relevant_docs = sec_filings_md_db.similarity_search(
      question,
      k=3,
      filter={
          "filing_type":{"$eq":sec_form_name}
      }
  )
  # print(relevant_docs)
  relevant_section_text = ""
  for relevant_text in relevant_docs:
      relevant_section_text += relevant_text.page_content + "\n\n"

  return relevant_section_text

global FROM_MARKDOWN
FROM_MARKDOWN = True

def query_database_sec(
            question: str,
            sec_form_name: str
    )->str:
        """This tool will query the SEC Filings database for a given question and form name, and it will retrieve
        the relevant text along from the SEC filings and the section names. This tool helps in answering questions
        from the sec filings.

        Args:
            question (str): _description_. Question to query the database for relevant documents
            sec_form_name (str): _description_. SEC FORM NAME that the question is talking about. It can be 10-K for yearly data and 10-Q for quarterly data. For quarterly data, it can be 10-Q2 to represent Quarter 2 and similarly for other quarters.

        Returns:
            str: Relevant context for the question from the sec filings
        """
        if not FROM_MARKDOWN:
          return query_database_unstructured_sec(question,sec_form_name)
        elif FROM_MARKDOWN:
          return query_database_markdown_sec(question,sec_form_name)

sec_form_system_msg = ""
llm_config = {"model":"gpt-4-turbo"}
for sec_form in sec_form_names:
    if sec_form == "10-K":
        sec_form_system_msg+= "10-K for yearly data, "
    elif "10-Q" in sec_form:
        quarter = sec_form[-1]
        sec_form_system_msg+= f"{sec_form} for Q{quarter} data, "
sec_form_system_msg = sec_form_system_msg[:-2]

earnings_call_system_message = ", ".join(earnings_call_quarter_vals)

system_msg = f"""You are a helpful financial assistant and your task is to select the sec_filings or earnings_call or financial_books to best answer the question.
You can use query_database_sec(question,sec_form) by passing question and relevant sec_form names like {sec_form_system_msg}
or you can use query_database_earnings_call(question,quarter) by passing question and relevant quarter names with possible values {earnings_call_system_message}
or you can use query_database_books(question) to get relevant documents from financial textbooks about valuation and investing philosophies. When you are ready to end the coversation, reply TERMINATE"""
     
print(system_msg)

from autogen import ConversableAgent
import os

llm_config = {"model":"gpt-4-turbo"}

os.environ['OPENAI_API_KEY'] = ""
user_proxy = ConversableAgent(
    name = "Planner Admin",
    system_message=system_msg,
    code_execution_config=False,
    llm_config=llm_config,
    human_input_mode="NEVER",
    is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
)
tool_proxy = ConversableAgent(
  name="Tool Proxy",
  system_message="Analyze the response from user proxy and decide whether the suggested database is suitable "
  ". Answer in simple yes or no",
  llm_config=False,
  # is_termination_msg=lambda msg: "exit" in msg.get("content",""),
  default_auto_reply="Please select the right database.",
  human_input_mode="ALWAYS",
  )

tools_dict = {
        "sec":[query_database_sec,"Tool to query SEC filings database"],
        "earnings_call": [query_database_earnings_call, "Tool to query earnings call transcripts database"],
    }

from autogen import register_function

for tool_name,tool in tools_dict.items():
  register_function(
      tool[0],
      caller=user_proxy,
      executor=tool_proxy,
      name = tool[0].__name__,
      description=tool[1]
  )

input_text = "What is the strategy of Google for artificial intelligence?"
chat_result = user_proxy.initiate_chat(
        recipient=tool_proxy,
        message=input_text,
        max_turns=10
    )

input_text = "What are the risk factors that Google faced this year?"
chat_result = user_proxy.initiate_chat(
        recipient=tool_proxy,
        message=input_text,
        max_turns=10
    )

input_text = "What was forward estimates of Google for the year 2023?"
chat_result = user_proxy.initiate_chat(
        recipient=tool_proxy,
        message=input_text,
        max_turns=10
    )

