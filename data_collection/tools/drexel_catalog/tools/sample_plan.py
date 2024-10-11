import requests
from bs4 import BeautifulSoup
import json
import time

base_url = 'https://catalog.drexel.edu'
majors_url = 'https://catalog.drexel.edu/majors/'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_major_urls():
    try:
        response = requests.get(majors_url, headers=headers, timeout=10)
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

def parse_plan_table(table):
    structured_plan = {}
    current_year = None
    current_term = None

    rows = table.find_all('tr')
    for row in rows:
        if 'plangridyear' in row.get('class', []):
            current_year = row.get_text(strip=True)
            structured_plan[current_year] = {}
        elif 'plangridterm' in row.get('class', []):  # Detect term headers
            terms = [term.get_text(strip=True) for term in row.find_all('th') if term.get_text(strip=True)]
            for term in terms:
                structured_plan[current_year][term] = {'courses': [], 'total_credits': 0}
        elif 'plangridsum' in row.get('class', []):  # Sum row for credits
            credits = [td.get_text(strip=True) for td in row.find_all('td', class_='hourscol')]
            term_names = list(structured_plan[current_year].keys())
            for i, credit in enumerate(credits):
                structured_plan[current_year][term_names[i]]['total_credits'] = credit
        else:  
            columns = row.find_all('td')
            for i in range(0, len(columns), 2): 
                course_col = columns[i]
                credit_col = columns[i + 1] if (i + 1) < len(columns) else None
                course_text = course_col.get_text(strip=True)
                credits = credit_col.get_text(strip=True) if credit_col else '0'

                term_index = i // 2
                term_names = list(structured_plan[current_year].keys())
                if course_text:
                    structured_plan[current_year][term_names[term_index]]['courses'].append({
                        'course': course_text,
                        'credits': credits if credits else '0'
                    })

    return structured_plan

def extract_course_plan(session, url):
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        plan_tables = soup.find_all('table', class_='sc_plangrid')
        parsed_plans = {}
        for i, table in enumerate(plan_tables):
            plan_name = f"Plan {i + 1}"
            parsed_plans[plan_name] = parse_plan_table(table)
        return parsed_plans
    except requests.RequestException as e:
        print(f"Error fetching course plan for URL {url}: {e}")
        return {}

def scrape_all_course_plans():
    major_urls = get_major_urls()
    all_course_plans = {}

    with requests.Session() as session:
        for url in major_urls:
            major_name = url.split('/')[-2]
            print(f'Scraping course plan for: {major_name}')
            course_plans = extract_course_plan(session, url)
            if course_plans:
                all_course_plans[major_name] = course_plans
            time.sleep(2)  

    return all_course_plans


all_course_plans = scrape_all_course_plans()
output_file = 'data_collection/tools/drexel_catalog/data/all_structured_course_plans.json'
with open(output_file, 'w') as file:
    json.dump(all_course_plans, file, indent=4)

print(f'All structured course plans saved to {output_file}')