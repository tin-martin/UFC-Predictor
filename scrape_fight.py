import requests
from bs4 import BeautifulSoup

def scrape_fight_info(soup):
    data = {}

    BONUS_MAP = {"http://1e49bc5171d173577ecd-1323f4090557a33db01577564f60846c.r80.cf1.rackcdn.com/fight.png":"fight of the night", "http://1e49bc5171d173577ecd-1323f4090557a33db01577564f60846c.r80.cf1.rackcdn.com/perf.png": "performance of the night", "http://1e49bc5171d173577ecd-1323f4090557a33db01577564f60846c.r80.cf1.rackcdn.com/ko.png": "knockout of the night"}
    bonuses = []
    data[ "fight of the night"] = False 
    data[ "performance of the night"] = False
    data[ "knockout of the night"] = False

    title_tag = soup.select_one("i.b-fight-details__fight-title")
  
    if not title_tag:
        return None

    # Remove any <img> tag (the arrow icon)
    for img in title_tag.find_all("img"):
        src = img["src"]
        if src in BONUS_MAP:
            data[BONUS_MAP[src]] = True
        img.extract()

    data["weight_class"] = title_tag.get_text(strip=True)  # "Lightweight Bout"

    return data

def scrape_fighter_info(fighter_url, fighter_id):
    r = requests.get(fighter_url, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    data = {}
    for li in soup.select(".b-list__info-box li"):
        key = li.select("i")[0].get_text().strip().replace(":","").replace(".","")
        if key in ["Height","Weight","Reach","Stance","DOB"]:
            data[f"{fighter_id}_{key.lower()}"] = li.get_text().strip().replace(":","").replace("\n","").replace(".","").replace(key,"").lstrip()
    data[f"{fighter_id}_current_record"] = soup.select_one("span.b-content__title-record").text.strip().replace("Record: ","")
    return data

def scrape_fight(url):
    """Scrape a UFCStats fight page using the HTML template structure."""
    data = {}
    data["fight_link"] = url

    r = requests.get(url, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # FIGHT INFO
    fight_info = scrape_fight_info(soup)

    data.update(fight_info)

    # FIGHTERS + W/L OUTCOME
    persons = soup.select(".b-fight-details__person")

    fighters = []
    for idx, p in enumerate(persons):
        outcome = p.select_one(".b-fight-details__person-status").text.strip()
        name_tag = p.select_one(".b-fight-details__person-name a")
        data[f"fighter{idx+1}_name"] = name_tag.text.strip()
        data[f"fighter{idx+1}_link"] = name_tag["href"]
        data[f"fighter{idx+1}_outcome"] = outcome

    fighter1_info = scrape_fighter_info(data["fighter1_link"], "fighter1")
    fighter2_info = scrape_fighter_info(data["fighter2_link"], "fighter2")
    data |= fighter1_info
    data |= fighter2_info
    
    # METHOD / ROUND / TIME
    info_items = soup.select(".b-fight-details__text .b-fight-details__text-item, "
                         ".b-fight-details__text .b-fight-details__text-item_first")

    meta = {}

    for item in info_items:
        # find the label
        label_tag = item.select_one(".b-fight-details__label")
        if not label_tag:
            continue

        label = label_tag.text.strip().replace(":", "")

        # special case: Method has a second <i> tag containing the value
        other_i_tags = item.find_all("i", recursive=False)

        if len(other_i_tags) >= 2:
            # second <i> is the value
            value = other_i_tags[1].text.strip()
        else:
            # normal case: label + text
            value = item.text.replace(label_tag.text, "").strip()

        meta[label] = value

    details_p = soup.select_one("p.b-fight-details__text:has(i.b-fight-details__label:-soup-contains('Details'))")

    if details_p:
        # remove the label text
        details = details_p.get_text(" ", strip=True).replace("Details:", "").strip()
    else:
        details = None

    data["method"]       = meta.get("Method") 
    data["finish_round"] = meta.get("Round")
    data["finish_time"]  = meta.get("Time")
    data["time_format"] = meta.get("Time format")
    data["referee"] = meta.get("Referee")
    data["details"] = details

    # TOTAL STATS TABLE
    total_table = soup.find_all("table")[0]
    rows = total_table.select("tbody tr")[0].select("td")

    def parse_two_rows(td):
        """Each stat cell has two <p>: first fighter 1, second fighter 2"""
        texts = [p.text.strip() for p in td.select("p")]
        return {
            "fighter1": texts[0],
            "fighter2": texts[1]
        }

    totals = {
        "KD": parse_two_rows(rows[1]),
        "sig_str": parse_two_rows(rows[2]),
        "sig_str_pct": parse_two_rows(rows[3]),
        "total_str": parse_two_rows(rows[4]),
        "td": parse_two_rows(rows[5]),
        "td_pct": parse_two_rows(rows[6]),
        "sub_att": parse_two_rows(rows[7]),
        "rev": parse_two_rows(rows[8]),
        "ctrl": parse_two_rows(rows[9]),
    }

    for key in totals:
        data[f"fighter1_total_{key}"] = totals.get(key)["fighter1"]
        data[f"fighter2_total_{key}"] = totals.get(key)["fighter2"]

    # PER-ROUND STATS
    per_round_tables = soup.select("table.b-fight-details__table.js-fight-table")
    per_round = {}

    for tbl in per_round_tables:
        # Find round headers
        round_headers = tbl.find_all("thead", class_="b-fight-details__table-row_type_head")

        round_data = {}
        fighter_rows = tbl.select("tbody tr")

        # Every "round header" corresponds to two rows: fighter1 + fighter2
        ROUND_STAT_KEYS = [
            "KD",
            "sig_str",
            "sig_pct",
            "total_str",
            "td",
            "td_pct",
            "sub_att",
            "rev",
            "ctrl",
            "head",
            "body",
            "leg",
            "distance",
            "clinch",
            "ground"
        ]

        for i, header in enumerate(round_headers):
            round_number = header.text.strip()
            row = fighter_rows[i]
            tds = row.select("td")
            temp = {}
            if(len(tds) == 10):
                temp =  {
                    "KD": parse_two_rows(tds[1]),
                    "sig_str": parse_two_rows(tds[2]),
                    "sig_pct": parse_two_rows(tds[3]),
                    "total_str": parse_two_rows(tds[4]),
                    "td": parse_two_rows(tds[5]),
                    "td_pct": parse_two_rows(tds[6]),
                    "sub_att": parse_two_rows(tds[7]),
                    "rev": parse_two_rows(tds[8]),
                    "ctrl": parse_two_rows(tds[9]),
                }
            elif(len(tds) == 9):
                temp = {
                    "sig_str": parse_two_rows(tds[1]),
                    "sig_pct": parse_two_rows(tds[2]),
                    "head": parse_two_rows(tds[3]),
                    "body": parse_two_rows(tds[4]),
                    "leg": parse_two_rows(tds[5]),
                    "distance": parse_two_rows(tds[6]),
                    "clinch": parse_two_rows(tds[7]),
                    "ground": parse_two_rows(tds[8]),
                }
            else:
                assert NameError
            if round_number in per_round:
                per_round[round_number] = per_round[round_number] | temp
            else: 
                per_round[round_number] = temp
   
    for r in range(1,6):
        round = f"round {r}"
        if(round in per_round):
            for key in ROUND_STAT_KEYS:
                data[f"fighter1_{round.replace(' ','')}_{key}"] = per_round[round][key]["fighter1"]
                data[f"fighter2_{round.replace(' ','')}_{key}"] = per_round[round][key]["fighter2"]
        else:
            for key in ROUND_STAT_KEYS:
                data[f"fighter1_{round.replace(' ','')}_{key}"] = None
                data[f"fighter2_{round.replace(' ','')}_{key}"] = None

    # CHECK FOR -- , - 
    for key in data:
        if data[key] == "---" or data[key] == "--" or data[key] == "-":
            data[key] = None

    return data


# EXAMPLE USAGE
if __name__ == "__main__":
    url = "http://ufcstats.com/fight-details/394802bb096b403e"
    data = scrape_fight(url)
    print(data)
   
