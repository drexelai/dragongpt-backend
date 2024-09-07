from langchain import hub
from langchain_community.document_loaders import WebBaseLoader
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import bs4

load_dotenv(dotenv_path="keys.env")

llm = ChatOpenAI(model="gpt-4-turbo-2024-04-09")

links = [
    "https://drexel.edu/admissions/undergrad/first-year",
    "https://drexel.edu/admissions/apply/undergrad-instructions/part-time-instructions",
    "https://drexel.edu/provost/policies-calendars/academic-calendars",
    "https://drexel.edu/admissions/apply/undergrad-instructions/transfer-instructions",
    "https://drexel.edu/admissions/apply/undergrad-instructions/prerequisites",
    "https://drexel.edu/admissions/apply/undergrad-instructions/deadlines",
    "https://drexel.edu/admissions/apply/undergrad-instructions/international-instructions",
    "https://drexel.edu/admissions/apply/undergrad-instructions/readmission",
    "https://drexel.edu/admissions/financial-aid-affordability/undergrad/tuition"
]

loader = WebBaseLoader(
    web_paths=(links)
)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=200)
splits = text_splitter.split_documents(docs)
vectorstore = Chroma.from_documents(
    documents=splits, embedding=OpenAIEmbeddings())

# Retrieve and generate using the relevant snippets of the blog.
retriever = vectorstore.as_retriever()
prompt = hub.pull("rlm/rag-prompt")


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

answer = rag_chain.invoke(
    "What is on Monday, March 18, 2024 at Drexel?")

print(answer)