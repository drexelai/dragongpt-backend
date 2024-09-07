import requests
from bs4 import BeautifulSoup

url = "https://catalog.drexel.edu/colleges/"

# The text file variable
text_file = open(r"data_collection\tools\drexel_catalog\colleges_links.txt", "w")

def parse_major_links(url):
  # Fetch the content from the URL
  response = requests.get(url)
  soup = BeautifulSoup(response.content, 'html.parser')
  reference_links = []

  for link in soup.find_all('a'):
      domain = "https://catalog.drexel.edu"
      if link.get('href').startswith('/undergraduate') or link.get('href').startswith('/graduate'):
        text = link.text.strip()  # Get the text inside the <a> tag
        text_file.write(f'[{text}] - ' + domain + link['href'] + '\n')
          # (f'{i}. href\n')
          # i += 1

  return reference_links

  # for link in soup.find_all('ul, {}'):
  #   # Find the div with the given id
  #   links = soup.find_all('li')
  #   for link in links: 
  #     # print(link)
  #     href = link.get('href')
  #     path_to_link = '/graduate'
  #     domain = "https://catalog.drexel.edu"
  #     if href and href.startswith(path_to_link):
  #       text_file.write(domain + link['href'] + '\n')
  # return reference_links

references = parse_major_links(url)

print(references)
text_file.close()
# Close it
# text_file.close()