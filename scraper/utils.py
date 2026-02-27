import random
import time
import requests
import threading
from scraper.headers import build_cffi_referer_headers
from typing import List, Dict, Any, Optional
from itertools import cycle
from proxies import PROXY_LIST
import csv


DEVICES_LIST = [
    "SM-A556B Build/A556BXXU4BYDC",
    "SM-A356B Build/A356BXXU4BYDC",
    "SM-A156B Build/A156BZBDEUB",
    "SM-A546B Build/A546BXXU5BYDB",
    "SM-A256B Build/A256BXXU2AXH1",
    "SM-S928B Build/S928BXXU4BYCG",
    "SM-S921B Build/S921BXXU4BYCG",
    "SM-S911B Build/S911BXXU6DYHD",
    "SM-S711B Build/S711BXXU3CYHD",
    "Pixel 9 Pro Build/AD1A.240905.004",
    "Pixel 9 Build/BP1A.250505.005",
    "Pixel 8a Build/AP2A.240905.003.C1",
    "Pixel 8 Pro Build/BP1A.250305.019",
    "Pixel 7a Build/AP2A.240705.004",
    "Pixel 7 Build/AP4A.250205.002",
    "CPH2573 Build/OPD2230201",
    "CPH2613 Build/OPD2230302",
    "XQ-EC72 Build/68.1.A.3.109",
    "XQ-ES72 Build/68.1.A.0.257",
    "XT2431-1 Build/U1TDS35M.29-14",
    "XT2343-7 Build/U1TPS34.28-10-1",
    "2312DRAABL Build/UKQ1.240311.001",
    "23090RA98G Build/SKQ1.221119.001",
    "A142 Build/UKQ1.240311.001",
]

DESKTOP_VERSION_MAP = {
    110: ("chrome110", "110.0.5481.177"),
    116: ("chrome116", "116.0.5845.187"),
    119: ("chrome119", "119.0.6045.199"),
    120: ("chrome120", "120.0.6099.224"),
    123: ("chrome123", "123.0.6312.122"),
    124: ("chrome124", "124.0.6367.201"),
    131: ("chrome131", "131.0.6778.264"),
    133: ("chrome133a", "133.0.6943.141"),
}

MOBILE_VERSION_MAP = {
    99: ("chrome99_android", "99.0.4844.88"),
    131: ("chrome131_android", "131.0.6778.264"),
}

MOBILE_PW_VERSION_MAP = {
    136: ("chrome136_android", "136.0.7103.60"),
    137: ("chrome137_android", "137.0.7151.61"),
    138: ("chrome138_android", "138.0.7204.179"),
    139: ("chrome139_android", "139.0.7258.158"),
    140: ("chrome140_android", "140.0.7339.155"),
    141: ("chrome141_android", "141.0.7390.111"),
    142: ("chrome142_android", "142.0.7444.138"),
    143: ("chrome143_android", "143.0.7499.192"),
    144: ("chrome144_android", "144.0.7559.132"),
    145: ("chrome145_android", "145.0.7632.45"),
    146: ("chrome146_android", "146.0.7680.16")
}

_STRIP_HEADERS = {
    ":method", ":path", ":scheme", ":authority",
    "host", "content-length", "transfer-encoding", "connection",
    "keep-alive", "proxy-connection", "upgrade",
}


class ProxyPool:
    def __init__(self):
        seen: set = set()
        unique: List[Dict] = []
        if not PROXY_LIST:
            raise Exception('Please add residential proxy list to proxies.py')
        for p in PROXY_LIST:
            key = p["username"]
            if key not in seen:
                seen.add(key)
                unique.append(p)
        self._proxies: List[Dict] = unique
        self._queue: List[Dict] = []
        self._lock = threading.Lock()

    def _refill(self) -> None:
        self._queue = self._proxies.copy()
        random.shuffle(self._queue)

    def _next(self) -> Dict:
        with self._lock:
            if not self._queue:
                self._refill()
            return self._queue.pop()

    def get_res_proxy(self) -> Dict[str, str]:
        p = self._next()
        auth = f"{p['username']}:{p['password']}@{p['host']}:{p['port']}"
        return {"http": f"http://{auth}", "https": f"http://{auth}"}

    def get_res_pw_proxy(self) -> Dict[str, str]:
        p = self._next()
        return {
            "server": f"http://{p['host']}:{p['port']}",
            "username": p["username"],
            "password": p["password"],
        }


def fetch_fresh_proxies(limit: int = 30) -> List[str]:
    sources = [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/https.txt",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=https&timeout=10000",
    ]
    proxies: List[str] = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for url in sources:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            for line in resp.text.splitlines():
                proxy = line.strip()
                if ":" in proxy:
                    proxies.append(proxy)
        except requests.RequestException:
            continue
    return list(dict.fromkeys(proxies))[:limit]


def get_static_proxy(user_agent: str, pw_proxy: bool, timeout: float = 5.0) -> Dict[str, str]:
    test_url = "https://www.google.com/robots.txt"
    headers = build_cffi_referer_headers(user_agent)
    for proxy in fetch_fresh_proxies():
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        try:
            resp = requests.get(test_url, proxies=proxies, headers=headers, timeout=timeout)
            if resp.status_code == 200 and resp.text.strip():
                return build_pw_proxies(proxy) if pw_proxy else build_proxies(proxy)
        except requests.RequestException:
            continue
    raise Exception("No workable proxy found")


def build_proxies(proxy: str) -> Dict[str, str]:
    host = proxy if "://" in proxy else f"http://{proxy}"
    return {"http": host, "https": host}


def build_pw_proxies(proxy: str) -> Dict[str, str]:
    host = proxy if "://" in proxy else f"http://{proxy}"
    return {"server": host}


def get_desktop_useragent() -> tuple:
    major = random.choice(list(DESKTOP_VERSION_MAP.keys()))
    impersonate, full_version = DESKTOP_VERSION_MAP[major]
    platform = random.choice([
        "Windows NT 10.0; Win64; x64", "Windows NT 11.0; Win64; x64", "Macintosh; Intel Mac OS X 10_15_7",
        "Macintosh; Intel Mac OS X 11_3_1", "Macintosh; Intel Mac OS X 11_6", "Macintosh; Intel Mac OS X 13_3_1",
        "Macintosh; Intel Mac OS X 14"
    ])
    user_agent = (
        f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{full_version} Safari/537.36"
    )
    return user_agent, impersonate


def get_mobile_useragent(is_pw_request) -> tuple:
    ver_mapping = MOBILE_PW_VERSION_MAP if is_pw_request else MOBILE_VERSION_MAP
    major = random.choice(list(ver_mapping.keys()))
    impersonate, full_version = ver_mapping[major]
    android_version = random.randint(9, 15)
    device = random.choice(DEVICES_LIST)
    user_agent = (
        f"Mozilla/5.0 (Linux; Android {android_version}.0; {device}) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{full_version} Mobile Safari/537.36"
    )
    return user_agent, impersonate


def generate_pw_useragent() -> str:
    platform = random.choice([
        "Windows NT 10.0; Win64; x64", "Windows NT 11.0; Win64; x64", "Macintosh; Intel Mac OS X 10_15_7",
        "Macintosh; Intel Mac OS X 11_3_1", "Macintosh; Intel Mac OS X 11_6", "Macintosh; Intel Mac OS X 13_3_1",
        "Macintosh; Intel Mac OS X 14"
    ])
    versions = {
        145: ["7632.116", "7632.109", "7632.76"],
        144: ["7559.116", "7559.60", "7559.59"],
        143: ["7499.147", "7499.146", "7499.40"],
        142: ["7444.235", "7444.171"],
        141: ["7388.102", "7388.88"],
        140: ["7325.200", "7325.182"],
        139: ["7263.89", "7263.57"],
        138: ["7207.101", "7207.83"],
        137: ["7150.89", "7150.55"],
        136: ["7098.120", "7098.102"]
    }
    major = random.choice(list(versions.keys()))
    patch = random.choice(versions[major])
    user_agent = (f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) "
                  f"Chrome/{major}.0.{patch} Safari/537.36")
    return user_agent


# def load_user_agents(csv_file="scraper/user_agents.csv"):
#     with open(csv_file, newline='', encoding="utf-8") as f:
#         reader = csv.reader(f)
#         return [row[0] for row in reader if row]
#
#
# user_agents = load_user_agents()
#
#
# def generate_pw_useragent():
#     user_agents_pool = cycle(user_agents)
#     ua = next(user_agents_pool)
#     return ua


def retry_with_backoff(func, retries: int = 6, base_delay: float = 1):
    for attempt in range(1, retries + 1):
        try:
            return func()
        except RuntimeError:
            if attempt == retries:
                raise
            sleep_and_pw_attemp(base_delay, attempt, retries)
        except Exception:
            if attempt == retries:
                raise
            sleep_and_pw_attemp(base_delay, attempt, retries)
    return None


def sleep_and_pw_attemp(base_delay, attempt, retries):
    sleep = base_delay * attempt + random.uniform(0, 2)
    time.sleep(sleep)
    print(repr(f"Retry attempt {attempt}/{retries - 1} — sleeping {sleep:.1f}s"))


def prepare_headers(har_headers: List[Dict]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for h in har_headers:
        name = h["name"].lower()
        if name in _STRIP_HEADERS or name.startswith(":"):
            continue
        headers[name.title()] = h["value"]
    return headers


def prepare_pw_google_cookies(pw_cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    fixed = []
    for c in pw_cookies:
        cookie = c.copy()
        if "sameSite" in cookie:
            ss = str(cookie["sameSite"]).capitalize()
            if ss not in ("Strict", "Lax", "None"):
                cookie.pop("sameSite", None)
            else:
                cookie["sameSite"] = ss
        cookie.pop("url", None)
        cookie["domain"] = ".google.com"
        cookie["path"] = "/"
        fixed.append(cookie)
    return fixed


def cookies_list_to_str(pw_cookies: List[Dict[str, Any]]) -> str:
    parts = []
    for c in pw_cookies:
        domain = c.get("domain", "")
        name = c.get("name", "")
        value = c.get("value", "")
        if not name or not domain:
            continue
        if "google.com" in domain or domain == "":
            parts.append(f"{name}={value}")
    return "; ".join(parts)
