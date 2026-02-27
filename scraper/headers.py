import re
import random
from typing import Dict

BRAND_MAP = {
    "136": ('"Not(A:Brand";v="8", "Chromium";v="136", "Google Chrome";v="136"',
            '"Not(A:Brand";v="8.0.0.0", "Chromium";v="{full}", "Google Chrome";v="{full}"'),
    "137": ('"Not(A:Brand";v="8", "Chromium";v="137", "Google Chrome";v="137"',
            '"Not(A:Brand";v="8.0.0.0", "Chromium";v="{full}", "Google Chrome";v="{full}"'),
    "138": ('"Not(A:Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            '"Not(A:Brand";v="8.0.0.0", "Chromium";v="{full}", "Google Chrome";v="{full}"'),
    "139": ('"Not(A:Brand";v="8", "Chromium";v="139", "Google Chrome";v="139"',
            '"Not(A:Brand";v="8.0.0.0", "Chromium";v="{full}", "Google Chrome";v="{full}"'),
    "140": ('"Not(A:Brand";v="8", "Chromium";v="140", "Google Chrome";v="140"',
            '"Not(A:Brand";v="8.0.0.0", "Chromium";v="{full}", "Google Chrome";v="{full}"'),
    "141": ('"Not(A:Brand";v="8", "Chromium";v="141", "Google Chrome";v="141"',
            '"Not(A:Brand";v="8.0.0.0", "Chromium";v="{full}", "Google Chrome";v="{full}"'),
    "142": ('"Not(A:Brand";v="8", "Chromium";v="142", "Google Chrome";v="142"',
            '"Not(A:Brand";v="8.0.0.0", "Chromium";v="{full}", "Google Chrome";v="{full}"'),
    "143": ('"Not(A:Brand";v="8", "Chromium";v="143", "Google Chrome";v="143"',
            '"Not(A:Brand";v="8.0.0.0", "Chromium";v="{full}", "Google Chrome";v="{full}"'),
    "144": ('"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            '"Not(A:Brand";v="8.0.0.0", "Chromium";v="{full}", "Google Chrome";v="{full}"'),
    "145": ('"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            '"Not:A-Brand";v="99.0.0.0", "Google Chrome";v="{full}", "Chromium";v="{full}"')
}

YEAR_MAP = {
    "136": "2025",
    "137": "2025",
    "138": "2025",
    "139": "2025",
    "140": "2025",
    "141": "2025",
    "142": "2025",
    "143": "2025",
    "144": "2025",
    "145": "2026"
}


def build_cffi_headers(user_agent: str, is_mobile: bool = False) -> Dict[str, str]:
    match = re.search(r"Chrome/([\d.]+)", user_agent)
    chrome_version = match.group(1) if match else "144.0.0.0"
    major = chrome_version.split(".")[0]
    headers: Dict[str, str] = {
        "User-Agent": user_agent,
        "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9, image/avif,image/webp,image/apng,*/*;q=0.8,"
                   "application/signed-exchange;v=b3;q=0.7"),
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-CH-UA": f'"Chromium";v="{major}", "Google Chrome";v="{major}", "Not_A Brand";v="99"',
        "Sec-CH-UA-Mobile": "?1" if is_mobile else "?0",
        "Sec-CH-UA-Platform": '"Android"' if is_mobile else '"Windows"',
        "Priority": "u=0, i",
        "Referer": "https://www.google.com/"}
    return headers


def build_cffi_referer_headers(user_agent: str, is_mobile: bool = False) -> Dict[str, str]:
    headers = build_cffi_headers(user_agent, is_mobile)
    headers["Sec-Fetch-Site"] = "none"
    headers.pop("Referer", None)
    return headers


def generate_pw_headers(user_agent: str, is_mobile: bool) -> Dict[str, str]:
    match = re.search(r"Chrome/([\d.]+)", user_agent)
    chrome_version = match.group(1) if match else "144.0.7559.132"
    major = chrome_version.split(".")[0]
    brand_short, brand_full_tpl = BRAND_MAP.get(
        major,
        (f'"Not(A:Brand";v="8", "Chromium";v="{major}", "Google Chrome";v="{major}"',
         f'"Not(A:Brand";v="8.0.0.0", "Chromium";v="{{full}}", "Google Chrome";v="{{full}}"'))
    brand_full = brand_full_tpl.replace("{full}", chrome_version)
    year = YEAR_MAP.get(major, "2025")
    platform_t = '"Windows"' if "Windows" in user_agent else '"Macintosh"'
    return {
        "accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "accept-language": "en-GB,en;q=0.9",
        "priority": "u=0, i",
        "sec-ch-prefers-color-scheme": random.choice(["light", "dark"]),
        "user-agent": user_agent,
        "sec-ch-ua": brand_short,
        "sec-ch-ua-full-version-list": brand_full,
        "sec-ch-ua-mobile": "?1" if is_mobile else "?0",
        "sec-ch-ua-model": '"Pixel 7"' if is_mobile else '""',
        "sec-ch-ua-platform": '"Android"' if is_mobile else platform_t,
        "sec-ch-ua-platform-version": '"13.0.0"' if is_mobile else '"15.0.0"',
        "sec-ch-ua-arch": '"arm"' if is_mobile else '"x86"',
        "sec-ch-ua-bitness": '"64"',
        "sec-ch-ua-wow64": "?0",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "x-browser-channel": "stable",
        "x-browser-copyright": f"Copyright {year} Google LLC. All Rights reserved.",
        "x-browser-year": year,
    }
