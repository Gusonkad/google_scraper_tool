import random
import logging
from typing import Dict, List, Any, Tuple, Coroutine
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from scraper.headers import generate_pw_headers
from scraper.utils import prepare_headers
import json

logger = logging.getLogger(__name__)

CAPTCHA_SIGNALS = [
    "captcha", "unusual traffic", "automated queries",
    "our systems have detected", "grecaptcha", "g-recaptcha",
    "sorry/index",
]
RATE_LIMIT_SIGNALS = ["service unavailable", "too many requests"]

HOMEPAGE_OK_SIGNALS = [
    'textarea[name="q"]',
    'input[name="q"]',
    'id="gbqf"',
    'action="/search"',
]

CHROMIUM_PATH = r"C:\Users\guson\AppData\Local\ms-playwright\chromium-1208\chrome-win64\chrome.exe"
FIREFOX_PATH = r"C:\Users\guson\AppData\Local\ms-playwright\firefox-1509\firefox\firefox.exe"
HAR_PATH = "google.har"


async def playwright_fallback(init_url: str, user_agent: str, layout_mode: str, pw_proxies: Dict) -> Tuple[
        str, Dict[str, str], None]:
    is_mobile = layout_mode == "mobile"
    context_conf = _viewport_and_screen(layout_mode)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            executable_path=CHROMIUM_PATH, headless=True, proxy=pw_proxies, slow_mo=random.randint(30, 80),
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled",
                  "--disable-infobars", "--disable-extensions", "--disable-component-extensions-with-background-pages",
                  "--use-fake-ui-for-media-stream"]
        )
        context = await browser.new_context(
            user_agent=user_agent, locale="en-GB", timezone_id="Europe/London", **context_conf,
            permissions=["geolocation", "notifications"],
            extra_http_headers=generate_pw_headers(user_agent, is_mobile),
            record_har_path=HAR_PATH, record_har_content="omit",
        )
        await context.add_init_script(_get_eval_js_media())
        page = await context.new_page()
        # await stealth_async(page)
        # if pw_cookies:
        #     try:
        #         await context.add_cookies(pw_cookies)
        #         logger.info(repr(f"Injected {len(pw_cookies)} cookies"))
        #     except Exception as exc:
        #         logger.warning(repr(f"Cookie injection error: {exc}"))

        await page.wait_for_timeout(random.randint(500, 1000))
        await page.goto("https://www.google.com/?hl=en", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(random.randint(3000, 4000))
        await _handle_consent(page)
        homepage_block = await _classify_page(page)
        if homepage_block:
            logger.warning(repr(f"Homepage blocked: {homepage_block}"))
            await context.close()
            await browser.close()
            raise RuntimeError(homepage_block)
        await _mouse_moves(page)
        await _scroll(page)
        # domain_cookies = await context.cookies("https://www.google.com")

        await page.goto(init_url.strip(), wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(random.randint(3000, 5000))
        await _handle_consent(page)
        search_block = await _classify_page(page)
        if search_block:
            logger.warning(repr(f"Search results blocked: {search_block}"))
            await context.close()
            await browser.close()
            raise RuntimeError(search_block)

        await page.wait_for_timeout(random.randint(1000, 2000))
        html = await page.content()

        search_cookies = await context.cookies("https://www.google.com/search?")
        logger.info(repr(f"Live cookie jar: {len(search_cookies)} cookies"))

        await context.close()
        await browser.close()
        # domain_cookie_dict = {c["name"]: c["value"] for c in domain_cookies}
        search_cookie_dict = {c["name"]: c["value"] for c in search_cookies}
        # cookie_dict = domain_cookie_dict.update(**search_cookie_dict)
        request_headers = _extract_headers_from_har(HAR_PATH)
        return html, request_headers, search_cookie_dict


async def _handle_consent(page) -> None:
    try:
        if page.url == "https://www.google.com/?hl=en" and "consent.google" not in page.url:
            return
        logger.info(repr(f"Consent page detected: {page.url}"))
        selectors = [
            ".saveButtonContainer input[value='Accept all']",
            ".saveButtonContainerNarrowScreen input[value='Accept all']",
            "form:has-text('Accept all')",
            "button:has-text('Accept all')",
            "button>div:has-text('Accept all')",
            "input[type=submit][value='Accept all']",
            "#L2AGLb",
            "button:has-text('Agree')",
            "[aria-label='Accept all']",
            "form[action*='consent.google.com/save'] input[type=submit][value='Accept all']",
            "input.baseButtonGm3.filledButtonGm3.button.searchButton[value='Accept all']"
        ]
        for sel in selectors:
            try:
                await page.wait_for_selector(sel, timeout=1000)
                await page.click(sel)
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(random.randint(500, 1000))
                logger.info(repr(f"Consent accepted: {sel}"))
                return
            except Exception:
                continue
        logger.warning(repr("Consent detected but no button matched"))
    except Exception as exc:
        logger.warning(repr(f"Consent handler error: {exc}"))


async def _mouse_moves(page) -> None:
    for _ in range(random.randint(2, 6)):
        await page.mouse.move(random.randint(80, 900), random.randint(80, 600), steps=random.randint(8, 20))
        await page.wait_for_timeout(random.randint(200, 700))


async def _scroll(page) -> None:
    for _ in range(random.randint(2, 4)):
        await page.mouse.wheel(0, random.randint(300, 800))
        await page.wait_for_timeout(random.randint(500, 1200))
    await page.mouse.wheel(0, -random.randint(200, 450))
    await page.wait_for_timeout(random.randint(300, 900))


def _viewport_and_screen(layout_mode: str) -> Dict:
    mobile_profiles = [
        {"viewport": {"width": 390, "height": 844}, "screen": {"width": 390, "height": 844},
         "device_scale_factor": 3, "is_mobile": True, "has_touch": True},
        {"viewport": {"width": 412, "height": 915}, "screen": {"width": 412, "height": 915},
         "device_scale_factor": 2.625, "is_mobile": True, "has_touch": True},
        {"viewport": {"width": 375, "height": 812}, "screen": {"width": 375, "height": 812},
         "device_scale_factor": 3, "is_mobile": True, "has_touch": True},
        {"viewport": {"width": 414, "height": 896}, "screen": {"width": 414, "height": 896},
         "device_scale_factor": 3, "is_mobile": True, "has_touch": True},
    ]
    desktop_profiles = [
        {"viewport": {"width": 1366, "height": 768}, "screen": {"width": 1920, "height": 1080},
         "device_scale_factor": 1, "is_mobile": False, "has_touch": False},
        {"viewport": {"width": 1440, "height": 900}, "screen": {"width": 2880, "height": 1800},
         "device_scale_factor": 2, "is_mobile": False, "has_touch": False},
        {"viewport": {"width": 1920, "height": 1080}, "screen": {"width": 1920, "height": 1080},
         "device_scale_factor": 1, "is_mobile": False, "has_touch": False},
        {"viewport": {"width": 1920, "height": 1080}, "screen": {"width": 2560, "height": 1440},
         "device_scale_factor": 1, "is_mobile": False, "has_touch": False},
        {"viewport": {"width": 1920, "height": 1080}, "screen": {"width": 3840, "height": 2160},
         "device_scale_factor": 2, "is_mobile": False, "has_touch": False},
        {"viewport": {"width": 1280, "height": 800}, "screen": {"width": 2560, "height": 1600},
         "device_scale_factor": 2, "is_mobile": False, "has_touch": False},
        {"viewport": {"width": 1504, "height": 1000}, "screen": {"width": 2256, "height": 1504},
         "device_scale_factor": 2, "is_mobile": False, "has_touch": True},
        {"viewport": {"width": 1920, "height": 1080}, "screen": {"width": 3440, "height": 1440},
         "device_scale_factor": 1, "is_mobile": False, "has_touch": False}
    ]
    if layout_mode == "mobile":
        return random.choice(mobile_profiles)
    return random.choice(desktop_profiles)


def _get_eval_js_media():
    return """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = {
                    runtime: {
                        onConnect: { addListener: () => {} },
                        onMessage: { addListener: () => {} },
                        connect: () => {},
                        sendMessage: () => {},
                    },
                    loadTimes: function() { return {}; },
                    csi: function() { return {}; },
                    app: { isInstalled: false },
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        const arr = [1,2,3,4,5,6,7].map(i => ({
                            name: 'Plugin ' + i, filename: 'plugin' + i + '.dll', description: '', length: 0,
                        }));
                        arr.__proto__ = PluginArray.prototype;
                        return arr;
                    },
                });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-GB', 'en'] });
                const _query = window.navigator.permissions && window.navigator.permissions.query;
                if (_query) {
                    window.navigator.permissions.query = (parameters) =>
                        parameters.name === 'notifications'
                            ? Promise.resolve({ state: Notification.permission })
                            : _query(parameters);
                }
            """


async def _classify_page(page) -> str:
    try:
        url = page.url
        html = await page.content()
        html_lower = html.lower()
        if "consent.google" in url:
            return "consent"
        for sig in CAPTCHA_SIGNALS:
            if sig in html_lower:
                logger.info(repr(f"Captcha signal found at playwright_fallback: {sig}"))
                return "captcha"
        for sig in RATE_LIMIT_SIGNALS:
            if sig in html_lower:
                logger.info(repr(f"Rate limit signal found at playwright_fallback: {sig}"))
                return "rate_limit"
        if "</head><body><noscript>" in html or "enable javascript" in html_lower:
            return "requires enable js"
        if "google.com/?" in url or url.rstrip("/").endswith("google.com"):
            has_search_box = any(sig in html for sig in HOMEPAGE_OK_SIGNALS)
            if not has_search_box:
                logger.warning(repr(f"Homepage loaded but search box missing — treating as block"))
                return "captcha"
        return ""
    except Exception as exc:
        logger.warning(repr(f"Page classifier error: {exc}"))
        return ""


def _extract_headers_from_har(har_path: str) -> Dict[str, str]:
    with open(har_path, "r", encoding="utf-8") as f:
        har = json.load(f)
    raw_headers = []
    for entry in har["log"]["entries"]:
        req = entry["request"]
        if req["method"] == "GET" and "www.google.com" in req["url"]:
            raw_headers = req["headers"]
            break
    headers = prepare_headers(raw_headers)
    for key in list(headers.keys()):
        if key.lower() in ("cookie", "referer", "host"):
            del headers[key]
    return headers
