import os
import json
from bs4 import BeautifulSoup
import requests

cwd = os.path.join("data_collection", "tools", "drexel_catalog")
# Create a directory to store the JSON files
output_dir = "course_desc_json_files"
os.makedirs(os.path.join(cwd, output_dir), exist_ok=True)

# Function to parse a course section
def parse_course_section(section):
    course = {}

    cdspacing_elements = section.find_all('span', class_='cdspacing')
    if len(cdspacing_elements) >= 3:
        course['Identifier'] = cdspacing_elements[0].get_text(strip=True).replace('\u00a0', ' ')
        course['Title'] = cdspacing_elements[1].get_text(strip=True)
    
    course['Number_of_credits'] = section.find('p', class_='courseblocktitle').text.split(" ")[-2]

    course['Description'] = section.find('p', class_='courseblockdesc').get_text(strip=True)

    for b_tag in section.find_all('b'):
        text = b_tag.get_text(strip=True)
        next_sibling_text = b_tag.next_sibling.strip()

        if 'College/Department' in text:
            course['College/Department'] = next_sibling_text
        elif 'Repeat Status' in text:
            course['Repeat Status'] = next_sibling_text
        elif 'Prerequisites' in text:
            course['Prerequisites'] = next_sibling_text

    if 'Prerequisites' not in course:
        course['Prerequisites'] = 'Null'

    return course

# Function to process each URL and save course information to JSON
def process_urls(file_name):
    try:
        with open(os.path.join(cwd, file_name), 'r') as opened_file:
            courses = []
            for line in opened_file:
                line = line.strip()
                if not line:
                    continue

                # Fetch the content from each URL line
                response = requests.get(line)
                if response.status_code != 200:
                    print(f"Failed to fetch {line}")
                    continue

                # Parse the HTML content using BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')

                # Define a list to hold course information
                subject_courses = []

                # Find all sections containing course information
                sections = soup.find_all('div', class_='courseblock')

                for section in sections:
                    course = parse_course_section(section)
                    subject_courses.append({"data":course, "url":line})
                courses += subject_courses
            # Write the data to a JSON file
            name = file_name.split(".")[0]
            json_filename = os.path.join(os.path.join(cwd, output_dir), f'{name}.json')
            with open(json_filename, 'w') as f:
                json.dump(courses, f, indent=6)

            print(f"{name} has been saved to {output_dir}")
    except FileNotFoundError:
        print(f"Cannot open the file: {file_name}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Call the function to process URLs
process_urls('undergrad_quarter_majors.txt')
process_urls('grad_quarter_majors.txt')
