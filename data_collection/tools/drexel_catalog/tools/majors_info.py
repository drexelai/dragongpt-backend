import requests
import json
import time
from bs4 import BeautifulSoup

base_url = 'https://catalog.drexel.edu'
majors_url = 'https://catalog.drexel.edu/majors/'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_major_urls(session):
    try:
        response = session.get(majors_url, headers=headers, timeout=10)
        response.raise_for_status() 
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

def extract_major_info(session, url):
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        major_info = {}
        sample_plan = None

        def extract_section_text(section_id):
            section = soup.find('div', {'id': section_id})
            return section.get_text(strip=True, separator=' ') if section else None

        major_info['About the Program'] = extract_section_text('textcontainer')
        major_info['Degree Requirements'] = extract_section_text('concentrationrequirementstextcontainer')
        major_info['Co-op/Career Opportunities'] = extract_section_text('coopcareeropportunitiestextcontainer')
        major_info['Facilities'] = extract_section_text('facilitiestextcontainer')
        major_info['Faculty'] = extract_section_text('facultycontainer')
        sample_plan = extract_section_text('sampleplanofstudytextcontainer')

        return major_info, sample_plan
    except requests.RequestException as e:
        print(f"Error fetching data for URL {url}: {e}")
        return None, None

def scrape_all_majors_info():
    with requests.Session() as session:
        major_urls = get_major_urls(session)
        all_majors_info = {}
        sample_plans = {}

        for url in major_urls:
            major_name = url.split('/')[-2]
            print(f'Scraping data for: {major_name}')
            
            # Skip majors that have already been scraped
            if major_name in all_majors_info:
                print(f'Skipping already scraped major: {major_name}')
                continue

            major_info, sample_plan = extract_major_info(session, url)
            if major_info:
                all_majors_info[major_name] = major_info
            if sample_plan:
                sample_plans[major_name] = sample_plan

            time.sleep(2)

        return all_majors_info, sample_plans

majors_data, sample_plans_data = scrape_all_majors_info()

majors_data_path = 'data_collection/tools/drexel_catalog/data/majors_data.json'
sample_plans_path = 'data_collection/tools/drexel_catalog/data/sample_plans_data.json'

with open(majors_data_path, 'w', encoding='utf-8') as majors_file:
    json.dump(majors_data, majors_file, ensure_ascii=False, indent=4)

with open(sample_plans_path, 'w', encoding='utf-8') as sample_plans_file:
    json.dump(sample_plans_data, sample_plans_file, ensure_ascii=False, indent=4)

print(f"Data has been successfully saved to '{majors_data_path}' and '{sample_plans_path}'")
