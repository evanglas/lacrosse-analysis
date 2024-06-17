from bs4 import BeautifulSoup
import requests
import csv
import pandas as pd
from tqdm import tqdm
import os
import csv
import aiohttp
import asyncio

base_url = "https://stats.ncaa.org/teams/history/MLA/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"
}


async def fetch_url(session, url, semaphore):
    await asyncio.sleep(0.5)
    async with semaphore:
        async with session.get(url, headers=headers) as response:
            data = await response.text()
            return (response.status, url, data)


async def make_requests(urls):
    semaphore = asyncio.Semaphore(3)

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)

        for status, url, content in results:
            print("STATUS CODE", status, url)
            print(content)


if __name__ == "__main__":
    team_ids = []
    team_urls = []
    school_ids = []
    for file in os.listdir("histories"):
        school_id = file.split("_")[1].split(".")[0]
        d = csv.DictReader(open("histories/" + file))

        for row in d:
            team_url = row.get("team_url", "")
            team_urls.append(team_url)
            team_ids.append(team_url.split("/")[-1])
            school_ids.append(school_id)
    df = pd.DataFrame(
        {"school_id": school_ids, "team_id": team_ids, "team_url": team_urls}
    )

    asyncio.run(make_requests(df["team_url"][30:50]))
