import json
import time
import random
from datetime import datetime, timezone
from scraper.google import GoogleFetcher
from queries import QUERIES
from scraper.utils import (
    get_desktop_useragent,
    get_mobile_useragent,
    generate_pw_useragent,
    ProxyPool,
    get_static_proxy)
import logging
import os


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

GREEN = "\033[92m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"


def main():
    proxy_pool = ProxyPool()
    layout_mode, res_proxy = check_mode_input()
    user_agent, impersonate = get_desktop_useragent() if layout_mode == "desktop" else get_mobile_useragent(False)
    logger.info(repr(f'Created user_agent: {user_agent}'))
    pw_user_agent = get_mobile_useragent(True)[0] if layout_mode == "desktop" else generate_pw_useragent()
    logger.info(repr(f'Created Playwright user_agent: {pw_user_agent}'))
    proxies = proxy_pool.get_res_proxy() if res_proxy else get_static_proxy(user_agent, False)
    logger.info(repr(f'CFFI initial proxy: {proxies}'))
    pw_proxies = proxy_pool.get_res_pw_proxy() if res_proxy else get_static_proxy(user_agent, True)
    logger.info(repr(f"Playwright initial proxy: {pw_proxies['server']}"))
    logger.info(repr(f'Create output directory'))
    os.makedirs("output", exist_ok=True)
    fetcher = GoogleFetcher(layout_mode, res_proxy, proxies, pw_proxies, pw_user_agent)
    summary = {"mode": layout_mode, "started_at": datetime.now(timezone.utc).isoformat(), "queries": []}
    queries = QUERIES.copy()
    random.shuffle(queries)
    process_queries(fetcher, queries, user_agent, impersonate, summary)
    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    with open("output/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def check_mode_input():
    layout_mode = ask_input(
        f"{GREEN}Please enter layout mode (desktop/mobile): {CYAN}",
        lambda v: v.lower() in ("desktop", "mobile"),
        "Allowed values are desktop or mobile"
    ).lower()
    is_res_proxy = ask_input(
        f"{GREEN}Do you want to use residential proxy (yes/no): {CYAN}",
        lambda v: v.lower() in ("y", "yes", "n", "no"),
        "Please answer yes or no"
    ).lower() in ("y", "yes")
    return layout_mode, is_res_proxy


def ask_input(prompt, validator, error_msg):
    while True:
        value = input(prompt).strip()
        if validator(value):
            return value
        logger.info(f"{RED}{error_msg}{RESET}")


def process_queries(fetcher, queries, user_agent, impersonate, summary):
    for i, query in enumerate(queries, 1):
        print(repr(f'Used query: {query}'))
        record = {"query": query, "status": "ok"}
        try:
            html, status = fetcher.fetch_google(query, user_agent, impersonate)
            logger.info(repr(f'Got success response html for query: {query}'))
            with open(f"output/{i:02d}.html", "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as e:
            record["status"] = str(e)
            logger.info(repr(f'Got bad response status: {record["status"]}'))
        summary["queries"].append(record)
        time.sleep(2)


if __name__ == "__main__":
    main()
