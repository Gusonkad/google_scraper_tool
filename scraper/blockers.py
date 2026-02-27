class BlockClassifier:
    def __init__(self, min_html_size: int = 50_000):
        self.min_html_size = min_html_size
        self.signals = {
            "captcha": ["captcha", "unusual traffic", "sorry/index", "captcha-form", "automated queries",
                        "our systems have detected", "id=\"recaptcha\"", "grecaptcha"],
            "consent": ["consent.google.com", "before you continue to google"],
            "requires enable js": ["</head><body><noscript>", "please enable javascript on your web browser",
                                   "enable javascript to use google search"],
            "js_redirect": ['<meta http-equiv="refresh"', "window.location =", "window.location.replace(",
                            "window.location.href ="],
        }

    def classify_block(self, request_type: str, response) -> str:
        if request_type == "CFFI":
            if response.status_code in (429, 503):
                return "rate_limit"
            if response.status_code == 403:
                return "captcha"
            text = response.text
        else:
            text = response
        text_lower = text.lower()
        if ('id="search"' in text or 'id="rso"' in text or 'class="g"' in text or 'data-ved' in text
                or 'jscontroller=' in text):
            return "ok"
        for label, keywords in self.signals.items():
            if any(k.lower() in text_lower for k in keywords):
                return label
        if len(text) < self.min_html_size:
            return "partial"
        return "ok"
