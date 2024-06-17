import asyncio
import aiohttp
import pandas as pd
import json
import scraping.parsing_functions as pf
import csv
import aiofiles

folders = [
    "legends",
    "coaches",
    "links",
    "records",
    "schedules",
    "team_page_stats",
    "venues",
]
parsing_functions = [
    pf.parse_team_legend,
    pf.parse_head_coaches,
    pf.parse_links,
    pf.parse_records,
    pf.parse_schedule,
    pf.parse_team_stats,
    pf.parse_venues,
]


async def make_request(session, url):
    async with session.get(url, headers=HEADERS) as response:
        return await response.text()


async def parse_response_and_write_to_csv(response, file):
    print(response)
    file.write(response)


async def main(urls):
    delay = 0.25  # Minimum delay between requests in seconds
    token_bucket = asyncio.Queue()  # Token bucket to control request rate

    # Fill the token bucket with initial tokens
    for _ in range(len(urls)):
        await token_bucket.put(None)

    async with aiohttp.ClientSession() as session:
        tasks = []
        async with aiofiles.open("tc_output.txt", mode="w", newline="\n") as file:

            for url in urls:
                # Consume a token from the token bucket
                await token_bucket.get()

                # Make the request
                response = await make_request(session, url)

                # Parse the response and write to CSV in parallel
                task = asyncio.create_task(
                    parse_response_and_write_to_csv(response, file)
                )
                tasks.append(task)

                # Add a token back to the bucket after the delay
                asyncio.create_task(fill_token_bucket_after_delay(delay, token_bucket))

            # Wait for all tasks to complete
            await asyncio.gather(*tasks)


async def fill_token_bucket_after_delay(delay, token_bucket):
    await asyncio.sleep(delay)
    await token_bucket.put(None)


if __name__ == "__main__":
    HEADERS = json.load(open("headers.json"))
    all_teams = pd.read_csv("all_team_histories.csv")
    urls = all_teams.team_url[:50]
    asyncio.run(main(urls))
