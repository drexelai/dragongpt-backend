import os
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
from openai import OpenAI
import sys
sys.path.append('./')
from data_collection import data_manager
import ast
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
import logging


load_dotenv("keys.env")

app = Flask(__name__)
# app.config['DEBUG'] = os.environ["DEBUG_FLASK"]

from flask_cors import CORS
CORS(app, origins=["http://localhost:3000", "https://drexelai.github.io"], supports_credentials=True)# Allowing for future credential usage

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
INSTRUMENTATION_CONNECTION_STRING = os.environ.get("APPINSIGHTS_CONNECTION_STRING")
tracer = Tracer(
    exporter=AzureExporter(connection_string=INSTRUMENTATION_CONNECTION_STRING),
    sampler=ProbabilitySampler(1.0)
)

# Set up the logger to send logs to Application Insights
handler = AzureLogHandler(connection_string=INSTRUMENTATION_CONNECTION_STRING)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def check_rag_with_openai_api(RAG, query):
    check_prompt = f"Does the following context answer the query?\n\nContext: {RAG}\n\nQuery: {query}\n\nAnswer with 'yes' or 'no' in lowercase only please."
    check_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions about Drexel University using the latest and most up to date information"},
                    {"role": "user", "content":check_prompt}
                ]
    )
    return check_response.choices[0].message.content

def parse_urls_from_rag(RAG):
    return [metadata['URL'] for metadata in [ast.literal_eval(d) for d in RAG.split("\n")] if 'URL' in metadata]

# Improve the RAG by adding more information from the web if the initial RAG does not answer the query
def improve_rag(RAG, query):
    check_answer = check_rag_with_openai_api(RAG, query)

    if check_answer.lower() != 'yes':
        urls = parse_urls_from_rag(RAG)
        # RAG += data_manager.fetch_content_from_urls(urls)
        search_results = data_manager.duckduckgo_search(query + " at Drexel University 2024")
        # print(search_results)
        for result in search_results:
            # print("fetching info")
            RAG += result["body"]
            moreinfo = data_manager.fetch_content_from_urls(result["href"])
            if result["href"] not in urls:
                RAG += moreinfo + result["href"]
                # print(result["href"])
                # print(moreinfo)
        if len(RAG) > 128000:
            RAG = RAG[:128000]
    return RAG

@app.route("/")
def test():
    return "Server is running"

def reformat_chat_data(chat_data):
    reformatted_data = []
    if not chat_data:
        return ""
    for entry in chat_data:
        speaker = "User" if entry['isUser'] else "Bot"
        reformatted_data.append(f"{speaker}: {entry['text']}\n")
    return "".join(reformatted_data)

@app.route("/query", methods=["POST"])
def query_llm():
    with tracer.span(name="query_llm_span") as span:
        try:
            data = request.get_json()
            query = data.get("query")

            logger.info(f"Received question: {query}")
            span.add_annotation("Processing query")

            priorConversation = data.get("priorConversation")
            reformatted_chat = reformat_chat_data(priorConversation)

            if not query:
                return jsonify({"detail": "Query is required"}), 400

            RAG = data_manager.query_from_index(query)
            RAG = improve_rag(RAG, query)
            system_prompt = open(os.path.join("prompts", "system.txt"), 'r').read()
            instructions = open(os.path.join("prompts", "instructions.txt"), 'r').read()
            output_format = "\nPlease answer only in a couple sentences and render the entire response in markdown but organize the code using level 2 headings and paragraphs. Feel free to use lists and other markdown features"
            user_prompt = f'Use any information from the current conversation history where needed:\n{reformatted_chat}\n\n{RAG}\n\n {instructions} \n\n{query} + {output_format}'
            def generate():
                full_content = ""
                stream = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        if content : #Error handling for missing data 
                            full_content += content
                            #print(content)  # Print the content for debugging purposes
                            yield content
                # print(f"Response to question \"{query}\" has been generated")
                logger.info(f"Response generated for question '{query}': {full_content}")

            return Response(generate(), content_type="text/plain-text")

        except Exception as e:
            print(e)
            return jsonify({"answer": str(e)}), 500

@app.route("/summarize-convo", methods=["POST"])
def summarize_convo():
    firstMessage = request.get_json()["message"]
    chatrename = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a message summarizer who summarizes a given message into 2-3 words"},
                {"role": "user", "content": firstMessage + "\n\nSummarize this message into 2-3 words and just return the message"}
            ]
        ).choices[0].message.content

    return {"messageSummary": chatrename}


@app.route("/blackboard", methods=["POST"])
def query_blackboard():

    response2 = "Your assignments this week: ENTP 205 Ready, Set, Fail: Discussion board post on business idea due Friday 11:59PM. ENTP 325 Early Stage Venture Funding: Cap table assignment due Wednesday 11:59PM. MATH 121: Problem Set 4 pages 79-81 textbook due Thursday before class. Suggested Time Budgeting Plan: Monday (Today) – Focus: Start and finish Cap Table Assignment for ENTP 325. Time Required: 2-3 hours (including research and calculations). Goal: Complete most, if not all, of this assignment since it’s due soonest. Tuesday – Focus: Finish up the Cap Table Assignment if any parts remain. Time Required: 1 hour (if needed for final touch-ups). Begin: MATH 121 Problem Set 4 to avoid rushing before class on Thursday. Time Required: 1-2 hours. Goal: Get at least halfway through the problem set. Wednesday – Focus: Complete the remaining part of MATH 121 Problem Set 4. Time Required: 1-2 hours. Goal: Finish the problem set and review answers if time allows. Thursday – Focus: Write the Discussion Board Post for ENTP 205. Time Required: 1-2 hours for writing and revising. Goal: Complete the post in time for submission on Friday. This plan ensures you’re prioritizing based on due dates and spreading out your workload for a balanced approach."


    def generateblackboard():
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "you will repeat back to me what I say"},
                {"role": "user", "content": response2 + "\n\n\norganize this more nicely"}
            ],
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                #print(content)  # Print the content for debugging purposes
                yield content
    return Response(generateblackboard(), content_type="text/plain-text")


if __name__ == "__main__":
        app.run(debug=os.getenv("DEBUG_FLASK", True), host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
