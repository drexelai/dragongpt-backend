import os
import time
import requests
from bs4 import BeautifulSoup
import json

base_url = "https://catalog.drexel.edu"
page_url = "https://catalog.drexel.edu/graduateprograms/"

output_directory = "data_collection/tools/drexel_catalog/data/"
output_file = os.path.join(output_directory, "graduate_programs.json")

os.makedirs(output_directory, exist_ok=True)

response = requests.get(page_url)
response.raise_for_status()
soup = BeautifulSoup(response.content, "html.parser")

program_links = soup.find_all('a', href=True)

urls = [base_url + link['href'] for link in program_links if link['href'].startswith('/graduate/')]

# Uncomment the following line for testing with the first 5 links
# urls = urls[:5]

program_data = []

failed_links = []

def extract_program_info(url):
    print(f"Scraping URL: {url}")

    program_info = {
        "program_name": None,
        "program_details": {
            "degree_awarded": None,
            "calendar_type": None,
            "minimum_credits": None,
            "additional_concentration_credits": None,
            "co_op_option": None,
            "cip_code": None,
            "soc_code": None,
            "note": None
        },
        "sections": {
            "about_the_program": {
                "overview": None,
                "goals_and_objectives": [],
                "examinations": None
            },
            "admission_requirements": {
                "overview": None,
                "requirements": [],
                "additional_info": None
            },
            "degree_requirements": {
                "core_courses": [],
                "electives": [],
                "capstone": []
            },
            "program_level_outcomes": None
        },
        "faculty": [],
        "url": url
    }

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve {url}: {e}")
        failed_links.append(url)
        return None
    
    soup = BeautifulSoup(response.content, "html.parser")

    title_element = soup.find('h1', class_='page-title')
    if title_element:
        program_info['program_name'] = title_element.text.strip()
        print(f"Program Name: {program_info['program_name']}")

    details = soup.find(id='textcontainer')
    if details:
        description_paragraphs = details.find_all('p')
        for paragraph in description_paragraphs:
            if 'Major:' in paragraph.text:
                fields = paragraph.text.split('<br>')
                for field in fields:
                    if 'Degree Awarded:' in field:
                        program_info['program_details']['degree_awarded'] = field.split(':')[-1].strip()
                    elif 'Calendar Type:' in field:
                        program_info['program_details']['calendar_type'] = field.split(':')[-1].strip()
                    elif 'Minimum Required Credits:' in field:
                        program_info['program_details']['minimum_credits'] = field.split(':')[-1].strip()
                    elif 'Additional credits' in field:
                        program_info['program_details']['additional_concentration_credits'] = field.split(':')[-1].strip()
                    elif 'Co-op Option:' in field:
                        program_info['program_details']['co_op_option'] = field.split(':')[-1].strip()
                    elif 'CIP code:' in field:
                        program_info['program_details']['cip_code'] = field.split(':')[-1].strip()
                    elif 'SOC code:' in field:
                        program_info['program_details']['soc_code'] = field.split(':')[-1].strip()
                    elif 'Note:' in field:
                        program_info['program_details']['note'] = field.split(':')[-1].strip()

    sections = {
        'textcontainer': 'about_the_program',
        'admissionrequirementstextcontainer': 'admission_requirements',
        'programleveloutcomestextcontainer': 'program_level_outcomes'
    }

    for section_id, section_key in sections.items():
        section = soup.find(id=section_id)
        if section:
            if section_key == 'about_the_program':
                overview_text = section.get_text(separator='\n', strip=True)
                program_info['sections'][section_key]['overview'] = overview_text
                print(f"Overview of About the Program extracted.")

            if section_key == 'admission_requirements':
                overview_text = section.find('h2').text if section.find('h2') else None
                requirements_list = [li.get_text(strip=True) for li in section.find_all('li')] if section.find_all('li') else []
                additional_info = section.get_text(separator='\n', strip=True)
                program_info['sections'][section_key]['overview'] = overview_text
                program_info['sections'][section_key]['requirements'] = requirements_list
                program_info['sections'][section_key]['additional_info'] = additional_info
                print(f"Admission requirements extracted.")

    degree_section = soup.find(id='degreerequirementstextcontainer')
    if degree_section:
        course_groups = {'Core Courses': 'core_courses', 'Electives': 'electives', 'Capstone': 'capstone'}
        current_group = None

        rows = degree_section.find_all('tr')
        for row in rows:
            area_header = row.find('span', class_='courselistcomment areaheader')
            if area_header:
                header_text = area_header.get_text(strip=True)
                if header_text in course_groups:
                    current_group = course_groups[header_text]
            else:
                course = {
                    "course_code": None,
                    "course_title": None,
                    "credits": None
                }
                code_col = row.find('td', class_='codecol')
                title_col = row.find('td', class_='titlecol')
                credits_col = row.find('td', class_='hourscol')

                if code_col:
                    course["course_code"] = code_col.get_text(strip=True)
                if title_col:
                    course["course_title"] = title_col.get_text(strip=True)
                if credits_col:
                    course["credits"] = credits_col.get_text(strip=True)

                if current_group and (course["course_code"] or course["course_title"] or course["credits"]):
                    program_info['sections']['degree_requirements'][current_group].append(course)
        
        print(f"Degree requirements for program extracted.")

    faculty_section = soup.find(id='facultycontainer')
    if faculty_section:
        faculty_list = faculty_section.find_all('div', class_='facitem')
        for faculty_member in faculty_list:
            faculty_info = faculty_member.get_text(separator=' ', strip=True)
            program_info['faculty'].append(faculty_info)
        print(f"Faculty information extracted.")

    return program_info

for url in urls:
    program_info = extract_program_info(url)
    if program_info:
        program_data.append(program_info)

    time.sleep(2)  # Delay of 2 seconds

with open(output_file, 'w', encoding='utf-8') as json_file:
    json.dump(program_data, json_file, ensure_ascii=False, indent=4)

print(f"Data has been successfully saved to {output_file}")

if failed_links:
    print(f"Failed links: {failed_links}")
else:
    print("All links were successfully scraped.")
