import asyncio
import logging
import urllib.parse
from functools import partial
from urllib.parse import urlencode
from curl_cffi import requests as curl_requests
from parsel import Selector
from scraper.blockers import BlockClassifier
from scraper.fallback import playwright_fallback
from scraper.headers import build_cffi_headers, build_cffi_referer_headers
from scraper.utils import (
    generate_pw_useragent,
    get_desktop_useragent,
    get_mobile_useragent,
    ProxyPool,
    get_static_proxy,
    retry_with_backoff
)

logger = logging.getLogger(__name__)


class GoogleFetcher:
    def __init__(self, layout_mode, res_proxy, proxies, pw_proxies, pw_user_agent):
        self.initial_request = True
        self.layout_mode = layout_mode
        self.is_mobile = layout_mode == "mobile"
        self.res_proxy = res_proxy
        self.proxies = proxies
        self.pw_proxies = pw_proxies
        self.request_type = "CFFI"
        self.cffi_result, self.pw_result = None, None
        self.timeout = 30
        self._session = curl_requests.Session()
        self.cffi_session_cookies = {}
        self.proxy_pool = ProxyPool()
        self.req_headers, self.cookie_dict = {}, {}
        self.deep_link, self.pw_user_agent = '', pw_user_agent

    def fetch_google(self, query: str, user_agent: str, impersonate: str):
        classifier = BlockClassifier()
        search_url = "https://www.google.com/search"
        params = {"q": query, "hl": "en", "gl": "gb", "pws": "0"}
        self.deep_link = f"{search_url}?{urllib.parse.urlencode(params)}"

        def run_with_rotation():
            nonlocal user_agent, impersonate
            if not self.cookie_dict or (self.request_type == "CFFI" and self.cffi_result != "ok"):
                if not self.initial_request:
                    self._prepare_pw()
                return self._process_playwright_session_logic(query, None, classifier)
            return self._run(query, user_agent, impersonate, search_url, params, classifier)

        return retry_with_backoff(partial(run_with_rotation))

    def _run(self, query: str, user_agent: str, impersonate: str, search_url: str, params: dict,
             classifier: BlockClassifier):
        self.request_type = "CFFI"
        if not self.cffi_result or self.cffi_result != "ok":
            self._create_cffi_session(user_agent, impersonate)
        resp = self._search_request(search_url, params, user_agent, impersonate)
        logger.info(repr(f"CFFI status: {resp.status_code}"))
        self.cffi_result = classifier.classify_block("CFFI", resp)
        logger.info(repr(f"CFFI result: {self.cffi_result}"))
        if self.cffi_result == "ok":
            return resp.text, "ok (curl_cffi)"
        self.proxies = self.proxy_pool.get_res_proxy() if self.res_proxy else get_static_proxy(user_agent, False)
        logger.info(repr(f'CFFI rotated proxy: {self.proxies}'))
        return self._process_playwright_session_logic(query, resp, classifier)

    def _create_cffi_session(self, user_agent: str, impersonate: str) -> None:
        try:
            headers = build_cffi_referer_headers(user_agent, self.is_mobile)
            ss_req = self._session.get(
                "https://www.google.com/?hl=en",
                headers=self.req_headers if self.req_headers else headers,
                # impersonate=impersonate,
                proxies=self.proxies,
                timeout=self.timeout,
                allow_redirects=True,
                cookies=self.cookie_dict if self.cookie_dict else {},
                verify=True
            )
            if ss_req.status_code == 200:
                self.cffi_session_cookies = ss_req.cookies.get_dict()
            logger.info(repr(f"CFFI session status: {ss_req.status_code}"))
        except Exception as exc:
            logger.warning(repr(f"CFFI session failed: {exc}"))

    def _search_request(self, url: str, params: dict, user_agent: str, impersonate: str):
        # headers = {**self.request_headers}
        headers = build_cffi_headers(user_agent, self.is_mobile)
        headers.update({"User-Agent": user_agent})
        logger.info(repr(f"CFFI search: {url}?{urllib.parse.urlencode(params)}"))
        return self._session.get(
            url,
            params=params,
            headers=self.req_headers if self.req_headers else headers,
            # impersonate=impersonate,
            proxies=self.proxies,
            timeout=self.timeout,
            cookies=self.cookie_dict if self.cookie_dict else self.cffi_session_cookies,
            allow_redirects=True,
            verify=True
        )

    def _process_playwright_session_logic(self, query, resp, classifier):
        self.initial_request = False
        self.deep_link = self._parse_js_redirect(query, resp)
        self.request_type = "playwright"
        pw_html, self.req_headers, self.cookie_dict = asyncio.run(
            playwright_fallback(self.deep_link, self.pw_user_agent, self.layout_mode, self.pw_proxies))
        self.pw_result = classifier.classify_block("playwright", pw_html)
        logger.info(repr(f"Playwright result: {self.pw_result}"))
        if self.pw_result != "ok":
            self._prepare_pw()
            raise RuntimeError(self.pw_result)
        return pw_html, "ok (playwright)"

    def _parse_js_redirect(self, query: str, resp) -> str:
        if self.cffi_result == "requires enable js":
            param_q = urlencode({"q": query})
            for href in Selector(text=resp.text).css("a::attr(href)").getall():
                if param_q in href and href.startswith("/search"):
                    return f"https://www.google.com{href}"
        return self.deep_link

    def _prepare_pw(self):
        self.pw_user_agent = get_mobile_useragent(True)[0] if self.is_mobile else generate_pw_useragent()
        self.pw_proxies = self.proxy_pool.get_res_pw_proxy() if self.res_proxy else get_static_proxy(
            self.pw_user_agent, True)
        logger.info(repr(f"Playwright used URL: {self.deep_link}"))
        logger.info(repr(f"Playwright rotated proxy: {self.pw_proxies['server']}"))
        logger.info(repr(f"Playwright rotated user_agent: {self.pw_user_agent}"))
