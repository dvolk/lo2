import sys
from bs4 import BeautifulSoup

def extract_youtube_links(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    base_url = "https://www.youtube.com"
    for link in soup.find_all('a', href=True):
        href = link['href']
        if 'watch?v=' in href:
            print(base_url + href)

def main():
    html_content = sys.stdin.read()
    extract_youtube_links(html_content)

if __name__ == "__main__":
    main()
