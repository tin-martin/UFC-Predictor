from bs4 import BeautifulSoup
import pandas as pd
import requests
import re
import os 
import csv
import scrape_fight
import math

def save_row(row,idx):
    CSV_PATH = f"/Users/martintin/PycharmProjects/UFCProject/data/UFCData{idx}.csv"
    file_exists = os.path.exists(CSV_PATH)

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())

        # Write header only if file didn't exist before
        if not file_exists:
            writer.writeheader()

        writer.writerow(row)



def scrape_event_info(soup):
       # direct extraction via class
    event_name = soup.select_one("span.b-content__title-highlight").text.strip()
    
    info_box = soup.select_one(".b-list__info-box")
    if not info_box:
        return None

    items = info_box.select("li.b-list__box-list-item")

    event_date = None
    event_location = None

    for li in items:
        title_tag = li.select_one(".b-list__box-item-title")
        if not title_tag:
            continue

        title = title_tag.text.strip()
        
        # The text after <i> tag is contained in li.text BUT includes the title
        # So remove the title part to get the value
        raw_text = li.get_text(strip=True)
        value = raw_text.replace(title, "").strip()

        if title.startswith("Date"):
            event_date = value
        elif title.startswith("Location"):
            event_location = value

    return {
        "event_date": event_date,
        "event_location": event_location,
        "event_name": event_name
    }


FILE_SAVE_FREQ = 100
url = "http://ufcstats.com/statistics/events/completed?page=all"
html = requests.get(url).text
soup = BeautifulSoup(html, "html.parser")

event_links = []

table = soup.find("table", class_="b-statistics__table-events")
for a in table.find_all("a", href=True):
    event_links.append(a["href"])


out = []
#if continue, file_idx ==> next file index
file_idx = 0
#if continue, start from 
last_event_link = event_links[0]
for idx, event_link in enumerate(event_links[event_links.index(last_event_link)+1:]):
    if(idx % FILE_SAVE_FREQ == 0):
        file_idx += 1
    html = requests.get(event_link).text
    soup = BeautifulSoup(html, "html.parser")

    fight_links = []

    for row in soup.find_all("tr", onclick=True):
        onclick = row["onclick"]
        # Extract URL inside doNav('...')
        match = re.search(r"doNav\('([^']+)'\)", onclick)
        if match:
            fight_links.append(match.group(1))
   # print("Found", len(fight_links), "fight links:")

    event_data = scrape_event_info(soup)
    event_data["event_link"] = event_link
    print(idx, event_data["event_name"])

    for fight_link in fight_links:
        fight_data = scrape_fight.scrape_fight(fight_link)      
        row = event_data | fight_data 
        save_row(row, file_idx)  
        