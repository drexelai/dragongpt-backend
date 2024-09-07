from pinecone import Pinecone
from pinecone import ServerlessSpec
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import os
import time
import json
from dotenv import load_dotenv
from itertools import islice
import unicodedata
import requests
from duckduckgo_search import DDGS

# Load environment variables
load_dotenv("keys.env") #not needed for deployment

# Initialize Pinecone and embedding model
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
spec = ServerlessSpec(cloud="aws", region="us-east-1")
index_name = "dragongpt"
index = pc.Index(index_name)

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Function to create an index in Pinecone
def make_index(index_name):
    if index_name in pc.list_indexes().names():
        pc.delete_index(index_name)

    pc.create_index(
        name=index_name,
        dimension=384,
        metric="cosine",
        spec=spec
    )

    while not pc.describe_index(index_name).status['ready']:
        time.sleep(1)
    print("Index Created")

# Function to create a vector from JSON data
def create_vector(json_data):
    return embedding_model.encode(json.dumps(json_data))

# Function to chunk text if it exceeds a specified length
def chunk_text_if_needed(text, max_tokens_per_chunk=256):
    """
    Splits the text into smaller chunks if it exceeds the max_tokens_per_chunk length.
    """
    tokens = text.split()
    if len(tokens) > max_tokens_per_chunk:
        return list(text_chunks(text, max_tokens=max_tokens_per_chunk))
    else:
        return [text]

# Helper function to break an iterable into chunks of a specified size
def chunks(iterable, batch_size=200):
    """A helper function to break an iterable into chunks of size batch_size."""
    it = iter(iterable)
    chunk = tuple(islice(it, batch_size))
    while chunk:
        yield chunk
        chunk = tuple(islice(it, batch_size))

# Function to split text into smaller chunks based on a maximum token count
def text_chunks(text, max_tokens=256):
    """Yield successive chunks of text."""
    words = text.split()
    for i in range(0, len(words), max_tokens):
        yield " ".join(words[i:i + max_tokens])

# Function to normalize text to remove non-ASCII characters
def normalize_text(text):
    # Normalize the text to remove non-ASCII characters
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

# Function to upload course descriptions to the Pinecone index
def upload_course_desc_files_to_index(filepath, batch_size=200, max_tokens_per_chunk=256):
    with open(filepath, "r") as f:
        data = json.load(f)

    pinecone_data = []
    for item in tqdm(data):
        data_item = item['data']
        description_chunks = chunk_text_if_needed(data_item['Description'], max_tokens_per_chunk)

        for chunk_index, description_chunk in enumerate(description_chunks):
            vector = create_vector(description_chunk)
            metadata = {
                'Identifier': data_item['Identifier'],
                'Title': data_item['Title'],
                'Number_of_credits': data_item['Number_of_credits'],
                'Description': description_chunk,
                'College/Department': data_item['College/Department'],
                'Repeat Status': data_item['Repeat Status'],
                'Prerequisites': data_item['Prerequisites'],
                'url': item['url']
            }
            pinecone_data.append({
                'id': f"{data_item['Identifier']}_chunk_{chunk_index}",  # Unique ID for each chunk
                'values': vector,
                'metadata': metadata
            })

    for ids_vectors_chunk in chunks(pinecone_data, batch_size=batch_size):
        index.upsert(vectors=ids_vectors_chunk)

    print("Added data to index")
    print("Here is what the index looks like:")
    print(index.describe_index_stats())

# Function to upload official Drexel data to the Pinecone index
def upload_official_drexel_data_to_index(filepath, batch_size=200, max_tokens_per_chunk=256):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    pinecone_data = []
    for item in tqdm(data):
        header = item['Header']
        url = item['URL']
        text = item['Text']
        
        # Chunk the text if necessary
        text_chunks = chunk_text_if_needed(text, max_tokens_per_chunk)
        
        for chunk_index, text_chunk in enumerate(text_chunks):
            vector = create_vector(text_chunk)
            metadata = {
                'Header': header,
                'URL': url,
                'Text_Chunk': text_chunk,
                'Chunk_Index': chunk_index
            }
            pinecone_data.append({
                'id': f"{url}_chunk_{chunk_index}",  # Unique ID for each chunk
                'values': vector,
                'metadata': metadata
            })

    for ids_vectors_chunk in chunks(pinecone_data, batch_size=batch_size):
        index.upsert(vectors=ids_vectors_chunk)

    print("Added data to index")
    print("Here is what the index looks like:")
    print(index.describe_index_stats())

# Function to upload student organization data to the Pinecone index
def upload_student_orgs_to_index(textfile, urlsfile, batch_size=200, max_tokens_per_chunk=256):
    # Load the organization data
    with open(textfile, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    
    # Load the URLs data
    with open(urlsfile, "r", encoding="utf-8", errors="replace") as f:
        urls_data = json.load(f)
    
    pinecone_data = []
    for item, url_item in tqdm(zip(data, urls_data)):
        org_name = normalize_text(item['Org Name'])
        description = normalize_text(item['Description'])
        url = url_item 

        # Combine text and chunk if necessary
        combined_text = f"{org_name} - {description}"
        text_chunks = chunk_text_if_needed(combined_text, max_tokens_per_chunk)

        for chunk_index, text_chunk in enumerate(text_chunks):
            vector = create_vector(text_chunk)
            metadata = {
                'Org Name': org_name,
                'Description': description,
                'URL': url,
                'Text_Chunk': text_chunk,
                'Chunk_Index': chunk_index
            }

            pinecone_data.append({
                'id': f"{org_name}_chunk_{chunk_index}",  # Unique ID for each chunk
                'values': vector,
                'metadata': metadata
            })

    # Batch upload to Pinecone
    for ids_vectors_chunk in chunks(pinecone_data, batch_size=batch_size):
        index.upsert(vectors=ids_vectors_chunk)

    print("Added student organizations data to index")
    print("Here is what the index looks like:")
    print(index.describe_index_stats())

# Function to query the Pinecone index
def query_from_index(prompt:str, k=5) -> str:
    result = index.query(
        vector=embedding_model.encode(prompt).tolist(),
        top_k=k,
        include_metadata=True
    )
    matches = result['matches']
    metadata_list = [match['metadata'] for match in matches]
    return "\n".join(str(metadata) for metadata in metadata_list)

def fetch_content_from_urls(urls):
    content = ""
    if type(urls) == str:
        urls = [urls]
    for url in urls:
        if url.startswith("http") and not any(file in url.split('.')[-1] for file in ['asp', 'aspx', 'ashx']) and not "reddit" in url:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    content += f"\n{response.text}"
            except requests.RequestException as e:
                #print(f"Error fetching {url}: {e}")
                continue
    return content

def duckduckgo_search(query):
    return DDGS().text(query, max_results=3)

if __name__ == "__main__":
    pass
