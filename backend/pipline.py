from langchain_chroma import Chroma

from langchain_community.document_loaders import YoutubeLoader
from langchain_openai import OpenAIEmbeddings
from operator import itemgetter
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import json
import os
from dotenv import load_dotenv
from redis import Redis

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = os.environ.get("LANGSMITH_KEY")
os.environ["LANGCHAIN_PROJECT"] = "dynamo-card"
os.environ["LANGCHAIN_TRACING_V2"] = "true"


def format_docs(docs):
    seen = set()  # Set to store already seen contents
    unique_docs = []  # List to store unique documents

    for doc in docs:
        content = doc.page_content
        if content not in seen:
            seen.add(content)
            unique_docs.append(content)

    print(len(docs), " to ", len(unique_docs))  # Print the number of unique documents
    return "\n\n".join(unique_docs)  # Join and return the unique documents


def load_json(json_string):
    print(json_string)
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return None


def run(url: str, task_id: str, redis: Redis):
    loader = YoutubeLoader.from_youtube_url(
        url,
        add_video_info=False,
    )
    docs = loader.load()
    summary_temple_2 = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                As an expert in content organization, your task is to analyze the transcript of a lecture video provided below.
                Please evenly divide the transcript into three distinct chapters.
                Each chapter name should only represent in professional terminologies.
                Ensure that the chapters are arranged in a logical order that reflects the progression of the lecture.
                Your division should help in clearly delineating the structure of the lecture's content, making it easier to navigate and understand.
                Summary of chapter should be in one sentence.

                Title: {title}
                Transcript:
                {context}

                Your anwser must respond as a JSON object with the following structure:
                    {{<chapter name>: <summary of chapter>,
                    <chapter name>: <summary of chapter>,
                    ...
                    }}

    """,
            ),
        ]
    )

    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

    summary_chain_2 = summary_temple_2 | llm | StrOutputParser()
    final_summary = summary_chain_2.invoke(
        {"title": "CS162 Lecture 2: Four Fundamental OS Concepts", "context": docs}
    )
    # print(final_summary)
    final_summary_json = json.loads(final_summary)

    chapter_list = list(final_summary_json.keys())
    chapter_list_value = list(final_summary_json.values())
    chapter_list_with_def = [
        key + ": " + value for key, value in zip(chapter_list, chapter_list_value)
    ]
    # print(chapter_list_with_def)
    redis.hset(
        f"task:{task_id}",
        mapping={
            "chapter_list": json.dumps(final_summary_json),
            "status": "Working on Sub Topics...",
        },
    )
    # print(final_summary)
    sub_topic_template = ChatPromptTemplate.from_template(
        """
    As an expert in content decomposition, your task is to analyze each high-level topic from the provided list.
    For each high-level topic, break it down into three distinct sub-topics.
    Ensure that the sub-topics for each main topic are arranged in a logical order that reflects the progression of the lecture and give a detailed understanding of the main topic.
    Provide a concise, one-sentence summary that captures the essence of each sub-topic.

    List of High-Level Topics:
    {high_level_topic_list}

    Your answer must be formatted as a JSON object with the following structure, DO NOT include any high_level_topic:
    {{
        "<sub_topic>": "<summary of sub-topic>",
        ...
    }}
    """
    )
    sub_summary_chain = sub_topic_template | llm | StrOutputParser()
    sub_summary = sub_summary_chain.invoke(
        {"high_level_topic_list": ",".join(chapter_list_with_def), "context": docs}
    )
    print("subsumm", sub_summary)
    redis.hset(
        f"task:{task_id}",
        mapping={"sub_chapter_list": sub_summary, "status": "Working on Terms..."},
    )
    sub_summary_json = json.loads(sub_summary)
    sub_summary_list = []
    for i in sub_summary_json:
        sub_summary_list.append(f"{i}: {sub_summary_json[i]}")
        # for j in sub_summary_json[i]:
        #     sub_summary_list.append(f"{j}: {sub_summary_json[i][j]}")

    embeddings = OpenAIEmbeddings(model="text-embedding-3")
    text_splitter = RecursiveCharacterTextSplitter(
        # Set a really small chunk size, just to show.
        chunk_size=1500,
        chunk_overlap=50,
        length_function=len,
        is_separator_regex=False,
    )
    doc_after_split = text_splitter.split_documents(docs)
    print(len(doc_after_split))
    embeddings = OpenAIEmbeddings()
    new_client = chromadb.EphemeralClient()
    openai_lc_client = Chroma.from_documents(
        doc_after_split,
        embeddings,
        client=new_client,
        collection_name="openai_collection",
    )

    retriever = openai_lc_client.as_retriever()
    RAG_template = ChatPromptTemplate.from_template(
        """
      You are a subject matter expert on extract most relative terminologies on the context

      Follow the instructions to create a list of terminologies:
      1. DO NOT include any similar terminologies contain in this list: [{used_terminologies}]
      2. One terminology can be a word or a phrase, at most extract two terminologies.
      3. All terminologies have to be unique and in lowercase
      4. Generate the coresponding detailed definition for the terminologies from context

      You MUST respond as a JSON object with the following structure:
      {{"<term>": "<definition>",
        ...
      }}

      Given the topic: {topic}

      Context: {context}
      """
    )
    rag_chain = (
        {
            "context": itemgetter("topic") | retriever | format_docs,
            "topic": itemgetter("topic"),
            "used_terminologies": itemgetter("used_terminologies"),
        }
        | RAG_template
        | llm
        | StrOutputParser()
    )
    used_terminologies = ""
    rag_result = {}
    for sub_summary in sub_summary_list:
        print("topic: ", sub_summary)
        rag_result_json = ""
        while not rag_result_json:
            rag_result_i = rag_chain.invoke(
                {"used_terminologies": used_terminologies, "topic": sub_summary}
            )
            rag_result_json = load_json(rag_result_i)
            # print(rag_result_json)
        rag_result.update(rag_result_json)
        # Serialize the cumulative result to JSON
        serialized_result = json.dumps(rag_result)
        # Store in Redis
        redis.hset(f"task:{task_id}", "term_list", serialized_result)
        print("Updated Redis with:", serialized_result)
        rag_result_list = list(rag_result.keys())
        used_terminologies = ", ".join(rag_result_list)
        # used_terminologies += rag_result_list_str+','
        # print("curr result", used_terminologies)
    redis.hset(
        f"task:{task_id}",
        mapping={
            "status": "completed",
        },
    )
    for i in rag_result:
        print(f"{i}: ".capitalize() + f"{rag_result[i]}".capitalize())
