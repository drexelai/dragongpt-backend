import requests
import json
import time
from bs4 import BeautifulSoup

base_url = 'https://catalog.drexel.edu'
minors_url = 'https://catalog.drexel.edu/minors/undergraduate/'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_minor_urls(session):
    try:
        response = session.get(minors_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        minor_urls = [
            base_url + a_tag['href']
            for a_tag in soup.find_all('a', href=True)
            if a_tag['href'].startswith('/undergraduate/')
        ]
        return minor_urls
    except requests.RequestException as e:
        print(f"Error fetching minor URLs: {e}")
        return []

def clean_text(text):
    return text.replace('\xa0', ' ').strip()

def extract_minor_info(session, url):
    try:
        print(f"Fetching data from URL: {url}")
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        minor_info = {}
        program_requirements = {
            "required_courses": [],
            "elective_courses": [],
            "total_credits": ""
        }

        def extract_section_text(section_header):
            header = soup.find(['h2', 'h3'], string=section_header)
            if header:
                paragraph = header.find_next('p')
                return clean_text(paragraph.get_text()) if paragraph else None
            return None

        minor_info['about'] = extract_section_text('About the Minor')

        requirements_header = soup.find('h3', string='Requirements')
        if requirements_header:
            requirements_list = requirements_header.find_next('ul')
            minor_info['requirements'] = [clean_text(li.get_text()) for li in requirements_list.find_all('li')] if requirements_list else []

        course_table = soup.find('table', {'class': 'sc_courselist'})
        if course_table:
            section = "required_courses"
            for row in course_table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    course_code = clean_text(cells[0].get_text())
                    course_name = clean_text(cells[1].get_text())
                    if "Select" in course_name or "or" in course_code:
                        section = "elective_courses"
                    else:
                        program_requirements[section].append(f"{course_code} - {course_name}")
                elif "Total Credits" in row.get_text():
                    program_requirements["total_credits"] = clean_text(cells[-1].get_text())

        minor_info['program_requirements'] = program_requirements
        return minor_info
    except requests.RequestException as e:
        print(f"Error fetching data for URL {url}: {e}")
        return None

def scrape_all_minors_info():
    with requests.Session() as session:
        minor_urls = get_minor_urls(session)
        all_minors_info = {}

        # Uncomment to limit to only the first 5 minors for testing
        # minor_urls = minor_urls[:5]

        for url in minor_urls:
            minor_name = url.split('/')[-2]
            print(f'Scraping data for: {minor_name}')

            if minor_name in all_minors_info:
                print(f'Skipping already scraped minor: {minor_name}')
                continue

            minor_info = extract_minor_info(session, url)
            if minor_info:
                all_minors_info[minor_name] = minor_info

            time.sleep(2)

        return all_minors_info

minors_data = scrape_all_minors_info()

minors_data_path = 'data_collection/tools/drexel_catalog/data/minors_data.json'

with open(minors_data_path, 'w', encoding='utf-8') as minors_file:
    json.dump(minors_data, minors_file, ensure_ascii=False, indent=4)

print(f"Data has been successfully saved to '{minors_data_path}'")
