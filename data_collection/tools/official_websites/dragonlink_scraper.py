import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm

def get_student_org_urls(driver_path, output_file=r'data_collection\tools\official_websites\official_website_files\drexel_student_orgs_urls.json', load_more_times=50):
    # Set up the WebDriver
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)

    # Open the webpage
    driver.get('https://drexel.campuslabs.com/engage/organizations')

    # Wait for the page to load
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # List to store hrefs
    hrefs = []

    # Scroll down and click the "Load More" button `load_more_times` times
    for _ in range(load_more_times):
        # Scroll down to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for the page to load more content

        try:
            # Locate the "Load More" button and click it
            load_more_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[.//span[text()="Load More"]]')))
            load_more_button.click()
            time.sleep(2)  # Wait for more content to load
        except Exception as e:
            print("No more 'Load More' button found or an error occurred:", e)
            break

        # Find all href elements on the page
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href")
            if href and href.startswith("https://drexel.campuslabs.com"):
                hrefs.append(href)

    # Remove duplicates
    hrefs = list(set(hrefs))

    # Save the hrefs to a JSON file
    with open(output_file, 'w') as file:
        json.dump(hrefs, file, indent=4)

    # Close the browser
    driver.quit()


def extract_org_details(input_file=r'data_collection\tools\official_websites\official_website_files\drexel_student_orgs_urls.json', output_file=r'data_collection\tools\official_websites\official_website_files\drexel_student_orgs_text.json', driver_path=''):
    # Load the URLs from the JSON file
    with open(input_file, 'r') as file:
        urls = json.load(file)

    # Set up the WebDriver
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)

    org_details = []

    # Loop over URLs with tqdm progress bar
    for url in tqdm(urls, desc="Extracting details", unit="URL"):
        driver.get(url)
        time.sleep(2)  # Wait for the page to load

        # Extract the relevant details
        org_name = ''
        description = ''
        contact_info = ''

        try:
            org_name = driver.find_element(By.TAG_NAME, 'h1').text
        except:
            pass

        try:
            description_elems = driver.find_elements(By.TAG_NAME, 'p')
            description = " ".join([elem.text for elem in description_elems])
        except:
            pass

        try:
            contact_info_elems = driver.find_elements(By.TAG_NAME, 'span') + driver.find_elements(By.TAG_NAME, 'div')
            contact_info = " ".join([elem.text for elem in contact_info_elems])
        except:
            pass

        org_details.append({
            "Org Name": org_name,
            "Description": description,
            "Contact Information": contact_info
        })

    # Save the organization details to a JSON file
    with open(output_file, 'w') as file:
        json.dump(org_details, file, indent=4)

    # Close the browser
    driver.quit()


# Example usage:
driver_path = r'data_collection\tools\official_websites\chromedriver.exe'  # Replace with the path to your chromedriver

# Step 1: Get the student organization URLs
#get_student_org_urls(driver_path)

# Step 2: Extract details from each organization page
extract_org_details(driver_path=driver_path)
