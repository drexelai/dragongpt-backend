import requests
from bs4 import BeautifulSoup
import json

base_url = 'https://catalog.drexel.edu'
start_url = 'https://catalog.drexel.edu/colleges/'

college_data = []

response = requests.get(start_url)
if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    h3_links = soup.find_all('h3')

    for h3 in h3_links:
        a_tag = h3.find('a')
        if a_tag:
            college_url = base_url + a_tag['href']
            college_response = requests.get(college_url)
            
            if college_response.status_code == 200:
                college_soup = BeautifulSoup(college_response.content, 'html.parser')
                
                text_container = college_soup.find('div', {'id': 'textcontainer', 'class': 'page_content tab_content'})
                special_programs_container = college_soup.find('div', {'id': 'specialprogramstextcontainer', 'class': 'page_content tab_content'})
                
                college_info = {
                    'name': a_tag.text,
                    'url': college_url,
                    'description': '',
                    'majors': [],
                    'minors': [],
                    'accelerated_degrees': [],
                    'certificates': [],
                    'special_programs': {
                        'description': '',
                        'study_abroad': '',
                        'enrichment_programs': '',
                        'accelerated_dual_degree_programs': [],
                        'accelerated_summer_courses': '',
                        'dance_part_time_professionals': ''
                    }
                }

                if text_container:
                    description_paragraphs = text_container.find_all('p')
                    description = ' '.join(p.get_text(strip=True) for p in description_paragraphs)
                    college_info['description'] = description

                    majors_section = text_container.find('h3', text='Majors')
                    if majors_section:
                        majors_list = majors_section.find_next('ul')
                        if majors_list:
                            college_info['majors'] = [li.get_text(strip=True) for li in majors_list.find_all('a')]

                    minors_section = text_container.find('h3', text='Minors')
                    if minors_section:
                        minors_list = minors_section.find_next('ul')
                        if minors_list:
                            college_info['minors'] = [li.get_text(strip=True) for li in minors_list.find_all('a')]

                    accelerated_degrees_section = text_container.find('h3', text='Accelerated Degrees')
                    if accelerated_degrees_section:
                        accelerated_degrees_list = accelerated_degrees_section.find_next('ul')
                        if accelerated_degrees_list:
                            college_info['accelerated_degrees'] = [li.get_text(strip=True) for li in accelerated_degrees_list.find_all('a')]

                    certificates_section = text_container.find('h3', text='Certificates')
                    if certificates_section:
                        certificates_list = certificates_section.find_next('ul')
                        if certificates_list:
                            college_info['certificates'] = [li.get_text(strip=True) for li in certificates_list.find_all('a')]

                if special_programs_container:
                    special_programs_description = special_programs_container.find('p')
                    if special_programs_description:
                        college_info['special_programs']['description'] = special_programs_description.get_text(strip=True)

                    study_abroad_section = special_programs_container.find('h3', text='Study Abroad')
                    if study_abroad_section:
                        study_abroad_paragraph = study_abroad_section.find_next('p')
                        if study_abroad_paragraph:
                            college_info['special_programs']['study_abroad'] = study_abroad_paragraph.get_text(strip=True)

                    enrichment_programs_section = special_programs_container.find('h3', text='Enrichment Programs')
                    if enrichment_programs_section:
                        enrichment_programs_paragraph = enrichment_programs_section.find_next('p')
                        if enrichment_programs_paragraph:
                            college_info['special_programs']['enrichment_programs'] = enrichment_programs_paragraph.get_text(strip=True)

                    accelerated_dual_degree_section = special_programs_container.find('h3', text='Accelerated Dual Degree Programs')
                    if accelerated_dual_degree_section:
                        accelerated_dual_degree_list = accelerated_dual_degree_section.find_next('ul')
                        if accelerated_dual_degree_list:
                            college_info['special_programs']['accelerated_dual_degree_programs'] = [li.get_text(strip=True) for li in accelerated_dual_degree_list.find_all('li')]

                    accelerated_summer_courses_section = special_programs_container.find('h3', text='Accelerated Summer Courses')
                    if accelerated_summer_courses_section:
                        accelerated_summer_courses_paragraph = accelerated_summer_courses_section.find_next('p')
                        if accelerated_summer_courses_paragraph:
                            college_info['special_programs']['accelerated_summer_courses'] = accelerated_summer_courses_paragraph.get_text(strip=True)

                    dance_part_time_professionals_section = special_programs_container.find('h3', text='Dance Part-time Professionals')
                    if dance_part_time_professionals_section:
                        dance_part_time_professionals_paragraph = dance_part_time_professionals_section.find_next('p')
                        if dance_part_time_professionals_paragraph:
                            college_info['special_programs']['dance_part_time_professionals'] = dance_part_time_professionals_paragraph.get_text(strip=True)

                college_data.append(college_info)

with open('data_collection/tools/drexel_catalog/data/college_info.json', 'w') as json_file:
    json.dump(college_data, json_file, indent=4)

print("Data savd to college_info.json")
