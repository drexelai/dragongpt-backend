import os
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
from openai import OpenAI
import sys
sys.path.append('./')
from data_collection import data_manager
import ast

load_dotenv("keys.env")

app = Flask(__name__)
# app.config['DEBUG'] = os.environ["DEBUG_FLASK"]

from flask_cors import CORS
CORS(app, origins=["http://localhost:3000", "https://drexelai.github.io"])

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


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
        RAG += data_manager.fetch_content_from_urls(urls)
        search_results = data_manager.duckduckgo_search(query + " at Drexel University 2024")
        for result in search_results:
            moreinfo = data_manager.fetch_content_from_urls(result["href"])
            if result["href"] not in urls:
                RAG += moreinfo + result["href"]
                #print(result["href"])
                #print(moreinfo)
    return RAG

@app.route("/")
def test():
    return "Server is running"

@app.route("/query", methods=["POST"])
def query_llm():
    try:
        data = request.get_json()
        query = data.get("query")
        if not query:
            return jsonify({"detail": "Query is required"}), 400

        RAG = data_manager.query_from_index(query)
        RAG = improve_rag(RAG, query)
        system_prompt = "You are a helpful assistant that answers questions about Drexel University using the latest and most up to date information. Do not hallucinate"
        user_prompt = f"{RAG}\n\nGiven the above context, accurately answer the following query. Forget everything you knew before and only use the information found in the context to answer the prompt. If you can't answer the prompt with the information provided, say that you're not sure and provide some helpful links to find the information. Think step by step, take a deep breath:\n\n{query}"
        output_format = "\nPlease answer only in a couple sentences and render the entire response in markdown."
        def generate():
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt + output_format}
                ],
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    #print(content)  # Print the content for debugging purposes
                    yield content
        print(f"Response to question {query} has been generated")
        return Response(generate(), content_type="text/plain-text")
    
    except Exception as e:
        print(e)
        return jsonify({"answer": str(e)}), 500

if __name__ == "__main__":
        app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))