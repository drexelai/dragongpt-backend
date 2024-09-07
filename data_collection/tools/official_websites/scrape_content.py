import requests
from bs4 import BeautifulSoup
import json
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv("keys.env")

# url_builder.scrape_and_export_urls()


def scrape_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract text content
        text = soup.get_text(separator=' ', strip=True)
        return text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

# Load the JSON file
with open(r'data_collection\tools\official_websites\official_website_files\drexel_urls.json', 'r') as file:
    url_data = json.load(file)

# Prepare a list to store the results
results = []

# Loop through the headers and URLs in the JSON data with a progress bar
for header, urls in url_data.items():
    for url in tqdm(urls, desc=f"Processing {header}", unit="url"):
        text = scrape_text_from_url(url)
        if text:
            results.append({
                'Header': header,
                'URL': url,
                'Text': text
            })

# Save the results to a JSON file
output_file = r'data_collection\tools\official_websites\official_website_files\scraped_text_data.json'
with open(output_file, 'w', encoding='utf-8') as file:
    json.dump(results, file, ensure_ascii=False, indent=4)

print(f"Scraping completed. Data saved to {output_file}.")