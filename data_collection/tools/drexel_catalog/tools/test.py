import requests
from bs4 import BeautifulSoup

base_url = 'https://catalog.drexel.edu'
majors_url = 'https://catalog.drexel.edu/majors/'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_major_urls():
    try:
        response = requests.get(majors_url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for bad HTTP codes
        soup = BeautifulSoup(response.content, 'html.parser')
        major_urls = [
            base_url + a_tag['href']
            for p in soup.find_all('p')
            for a_tag in p.find_all('a', href=True)
            if a_tag['href'].startswith('/undergraduate/')
        ]
        return major_urls
    except requests.RequestException as e:
        print(f"Error fetching major URLs: {e}")
        return []

major_links = get_major_urls()
print(major_links)