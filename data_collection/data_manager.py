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
from bs4 import BeautifulSoup

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


def upload_college_info_to_index(filepath, batch_size=200, max_tokens_per_chunk=256):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    pinecone_data = []
    for item in tqdm(data):
        college_name = item['name']
        description = item.get('description', '')
        majors = item.get('majors', [])
        minors = item.get('minors', [])
        accelerated_degrees = item.get('accelerated_degrees', [])
        certificates = item.get('certificates', [])
        special_programs = item.get('special_programs', {}).get('description', '')

        # Combine all relevant text fields for encoding and chunk if necessary
        combined_text = f"{college_name} - {description} Majors: {majors} Minors: {minors} Accelerated Degrees: {accelerated_degrees} Certificates: {certificates} Special Programs: {special_programs}"

        # Normalize and chunk the text
        text_chunks = chunk_text_if_needed(normalize_text(combined_text), max_tokens_per_chunk)

        for chunk_index, text_chunk in enumerate(text_chunks):
            vector = create_vector(text_chunk)
            metadata = {
                'name': college_name,
                'description': description,
                'majors': majors,
                'minors': minors,
                'accelerated_degrees': accelerated_degrees,
                'certificates': certificates,
                'special_programs': special_programs,
                'Text_Chunk': text_chunk,
                'Chunk_Index': chunk_index
            }

            pinecone_data.append({
                'id': f"{college_name}_chunk_{chunk_index}",  # Unique ID for each chunk
                'values': vector,
                'metadata': metadata
            })

    # Batch upload to Pinecone
    for ids_vectors_chunk in chunks(pinecone_data, batch_size=batch_size):
        index.upsert(vectors=ids_vectors_chunk)

    print("Added college info to index")
    print("Here is what the index looks like:")
    print(index.describe_index_stats())


def upload_graduate_programs_to_index(filepath, batch_size=100, max_tokens_per_chunk=256):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    pinecone_data = []
    for item in tqdm(data):
        program_name = item['program_name']

        # Normalize the program name to ensure it's ASCII
        program_name_ascii = unicodedata.normalize('NFKD', program_name).encode('ascii', 'ignore').decode('ascii')

        program_details = item.get('program_details', {})
        sections = item.get('sections', {})
        faculty = item.get('faculty', [])
        url = item.get('url', '')

        # Convert nested structures (dictionaries/lists) to JSON strings
        program_details_str = json.dumps(program_details) if isinstance(program_details, dict) else str(program_details)
        sections_str = json.dumps(sections) if isinstance(sections, dict) else str(sections)
        faculty_str = ', '.join(faculty) if isinstance(faculty, list) else str(faculty)

        # Combine all relevant text fields for encoding and chunk if necessary
        combined_text = f"Program Name: {program_name_ascii}\nDetails: {program_details_str}\nSections: {sections_str}\nFaculty: {faculty_str}"

        # Normalize and chunk the text
        text_chunks = chunk_text_if_needed(normalize_text(combined_text), max_tokens_per_chunk)

        for chunk_index, text_chunk in enumerate(text_chunks):
            vector = create_vector(text_chunk)
            metadata = {
                'program_name': program_name_ascii,  # Use the ASCII-safe program name
                'program_details': program_details_str,  # Use stringified version
                'sections': sections_str,  # Use stringified version
                'faculty': faculty_str,
                'url': url,
                'Text_Chunk': text_chunk,
                'Chunk_Index': chunk_index
            }

            # Ensure the vector ID is also ASCII
            vector_id = f"{program_name_ascii}_chunk_{chunk_index}"

            pinecone_data.append({
                'id': vector_id,  # Use the ASCII-safe ID
                'values': vector,
                'metadata': metadata
            })

    # Batch upload to Pinecone with smaller batch size
    for ids_vectors_chunk in chunks(pinecone_data, batch_size=batch_size):
        index.upsert(vectors=ids_vectors_chunk)

    print("Added graduate programs info to index")
    print("Here is what the index looks like:")
    print(index.describe_index_stats())

def upload_majors_to_index(filepath, batch_size=100, max_tokens_per_chunk=256):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    pinecone_data = []
    for major, major_info in tqdm(data.items()):
        # Normalize the major name to ensure it's ASCII-safe
        major_name_ascii = unicodedata.normalize('NFKD', major).encode('ascii', 'ignore').decode('ascii')

        # Extract information from the major_info
        about_the_program = major_info.get('About the Program', '')
        degree_requirements = major_info.get('Degree Requirements', '')
        coop_career_opportunities = major_info.get('Co-op/Career Opportunities', '')
        facilities = major_info.get('Facilities', '')
        faculty = major_info.get('Faculty', '')

        # Convert nested or list-based information to strings
        degree_requirements_str = json.dumps(degree_requirements) if isinstance(degree_requirements, dict) else str(degree_requirements)
        coop_career_opportunities_str = json.dumps(coop_career_opportunities) if isinstance(coop_career_opportunities, dict) else str(coop_career_opportunities)
        facilities_str = json.dumps(facilities) if isinstance(facilities, dict) else str(facilities)
        faculty_str = json.dumps(faculty) if isinstance(faculty, dict) else str(faculty)

        # Combine all relevant text fields for encoding and chunk if necessary
        combined_text = f"Major Name: {major_name_ascii}\nAbout the Program: {about_the_program}\nDegree Requirements: {degree_requirements_str}\nCo-op/Career Opportunities: {coop_career_opportunities_str}\nFacilities: {facilities_str}\nFaculty: {faculty_str}"

        # Normalize and chunk the text
        text_chunks = chunk_text_if_needed(normalize_text(combined_text), max_tokens_per_chunk)

        for chunk_index, text_chunk in enumerate(text_chunks):
            vector = create_vector(text_chunk)
            metadata = {
                'major_name': major_name_ascii,  # Use ASCII-safe major name
                'about_the_program': about_the_program,
                'degree_requirements': degree_requirements_str,
                'coop_career_opportunities': coop_career_opportunities_str,
                'facilities': facilities_str,
                'faculty': faculty_str,
                'Text_Chunk': text_chunk,
                'Chunk_Index': chunk_index
            }

            # Ensure the vector ID is also ASCII
            vector_id = f"{major_name_ascii}_chunk_{chunk_index}"

            pinecone_data.append({
                'id': vector_id,  # Use ASCII-safe ID
                'values': vector,
                'metadata': metadata
            })

    # Batch upload to Pinecone with smaller batch size
    for ids_vectors_chunk in chunks(pinecone_data, batch_size=batch_size):
        index.upsert(vectors=ids_vectors_chunk)

    print("Added majors info to index")
    print("Here is what the index looks like:")
    print(index.describe_index_stats())

def upload_minors_to_index(filepath, batch_size=100, max_tokens_per_chunk=256):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    pinecone_data = []
    for minor, minor_info in tqdm(data.items()):
        # Normalize the minor name to ensure it's ASCII-safe
        minor_name_ascii = unicodedata.normalize('NFKD', minor).encode('ascii', 'ignore').decode('ascii')

        # Extract information from the minor_info and replace `None` with empty strings
        about = minor_info.get('about', '') or ""
        requirements = minor_info.get('requirements', []) or []
        program_requirements = minor_info.get('program_requirements', {}) or {}

        # Convert nested structures (dictionaries/lists) to JSON strings
        requirements_str = ', '.join(requirements) if isinstance(requirements, list) else str(requirements)
        program_requirements_str = json.dumps(program_requirements) if isinstance(program_requirements, dict) else str(program_requirements)

        # Combine all relevant text fields for encoding and chunk if necessary
        combined_text = f"Minor Name: {minor_name_ascii}\nAbout: {about}\nRequirements: {requirements_str}\nProgram Requirements: {program_requirements_str}"

        # Normalize and chunk the text
        text_chunks = chunk_text_if_needed(normalize_text(combined_text), max_tokens_per_chunk)

        for chunk_index, text_chunk in enumerate(text_chunks):
            vector = create_vector(text_chunk)
            metadata = {
                'minor_name': minor_name_ascii,  # Use ASCII-safe minor name
                'about': about,  # Ensure 'about' is not None
                'requirements': requirements_str,
                'program_requirements': program_requirements_str,
                'Text_Chunk': text_chunk,
                'Chunk_Index': chunk_index
            }

            # Ensure the vector ID is also ASCII
            vector_id = f"{minor_name_ascii}_chunk_{chunk_index}"

            pinecone_data.append({
                'id': vector_id,  # Use ASCII-safe ID
                'values': vector,
                'metadata': metadata
            })

    # Batch upload to Pinecone with smaller batch size
    for ids_vectors_chunk in chunks(pinecone_data, batch_size=batch_size):
        index.upsert(vectors=ids_vectors_chunk)

    print("Added minors info to index")
    print("Here is what the index looks like:")
    print(index.describe_index_stats())

###########################
# Functions for Server.py #
###########################

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

def is_valid_url(url: str) -> bool:
    is_http = url.startswith("http")
    has_invalid_extension = any(file in url.split('.')[-1] for file in ['asp', 'aspx', 'ashx'])
    is_social_media = any(platform in url for platform in ["reddit", "tiktok", "linkedin", "instagram", "facebook", "twitter", "youtube"])
    return is_http and not has_invalid_extension and not is_social_media

# too slow, deprecating
def fetch_content_from_urls(urls):
    content = ""
    if type(urls) == str:
        urls = [urls]
    for url in urls:
        if is_valid_url(url) and "drexel.edu" in url:
            print(url)
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    content += soup.get_text().replace("\n", "")
            except requests.RequestException as e:
                #print(f"Error fetching {url}: {e}")
                continue
    return content

def duckduckgo_search(query):
    return DDGS().text(query, max_results=3, backend="lite")

if __name__ == "__main__":
    pass
