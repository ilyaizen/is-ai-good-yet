import requests
from bs4 import BeautifulSoup
import json
import time
import os
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)

def update_recent(start_page, end_page, master_file, recent_file):
    logging.info(f"Starting update from page {start_page} to {end_page}")

    # Load existing links from master file
    existing_links = set()
    if os.path.exists(master_file):
        with open(master_file, 'r', encoding='utf-8') as f:
            try:
                existing_links = set(json.load(f))
            except json.JSONDecodeError:
                logging.error("Invalid JSON in master file. Starting fresh.")

    logging.info(f"Loaded {len(existing_links)} existing links from {master_file}.")
    initial_count = len(existing_links)

    found_links = [] # To store all links found in this run (for refreshing)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for page in range(start_page, end_page + 1):
        url = f"https://histre.com/hn/?tags=+ai&page={page}"
        logging.info(f"Scraping {url}...")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                logging.warning(f"Failed to fetch page {page}: Status {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            blocks = soup.find_all('div', class_='col-lg')

            page_new_links = 0
            for block in blocks:
                link_element = block.find('a')  # noqa: F821
                if not link_element:
                    continue
                    
                href = link_element.get('href')
                if not href:
                    continue
                    
                found_links.append(href)  # Add to recent list regardless of existence
                if href not in existing_links:
                    existing_links.add(href)
                    page_new_links += 1

            logging.info(f"Page {page}: Found {page_new_links} NEW links (Total found: {len(found_links)}).")

            time.sleep(1)  # Polite delay

        except (requests.RequestException, OSError) as e:
            logging.error(f"Error on page {page}: {e}")
            time.sleep(5)

    # Save master file (with new links)
    with open(master_file, 'w', encoding='utf-8') as f:
        json.dump(list(existing_links), f, indent=2)

    # Save recent file (for refreshing)
    with open(recent_file, 'w', encoding='utf-8') as f:
        json.dump(list(set(found_links)), f, indent=2)

    added = len(existing_links) - initial_count
    logging.info(f"Update complete.")
    logging.info(f"Added {added} new links to {master_file}.")
    logging.info(f"Saved {len(set(found_links))} recent links to {recent_file} for refreshing.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update recent HN links from Histre")
    parser.add_argument("--start", type=int, default=1, help="Start page number")
    parser.add_argument("--end", type=int, default=2, help="End page number")
    parser.add_argument("--master", type=str, default="posted_links.json", help="Master JSON file")
    parser.add_argument("--recent", type=str, default="recent_links.json", help="Output file for recent links to refresh")

    args = parser.parse_args()

    update_recent(args.start, args.end, args.master, args.recent)
