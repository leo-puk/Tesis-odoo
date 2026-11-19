"""Fixed, deterministic admission rules. Unknown URLs are denied."""
import re
from html import unescape
from urllib.parse import urlparse, unquote


class Excluded(ValueError):
    pass


class SourcePolicy:
    def __init__(self, catalog):
        # Inputs: catalog.
        # Does: Validate and index the reviewed URL and exclusion catalog.
        # Output: A source policy instance.
        required = {"allowed_urls", "excluded_urls", "oca_repositories", "oca_addons"}
        if not isinstance(catalog, dict) or not required <= catalog.keys():
            raise ValueError("Catalog requires allowed_urls, excluded_urls, oca_repositories, oca_addons")
        if any(not isinstance(catalog[k], list) or any(not isinstance(x, str) or not x for x in catalog[k]) for k in required):
            raise ValueError("Catalog entries must be lists of nonempty strings")
        if not catalog["oca_repositories"] or not catalog["oca_addons"]:
            raise ValueError("A populated OCA repository/addon catalog is required")
        self.allowed = set(catalog["allowed_urls"])
        self.excluded = set(catalog["excluded_urls"])
        self.repos = {x.lower().strip("/") for x in catalog["oca_repositories"]}
        self.pattern = re.compile(r"(?<![\w])(?:" + "|".join(re.escape(x) for x in catalog["oca_addons"]) + r")(?![\w])", re.I)

    def url(self, url):
        # Inputs: url.
        # Does: Validate scheme, host, reviewed URL and excluded identifiers.
        # Output: Successful validation or an exclusion error.
        p = urlparse(url)
        if (p.scheme != "https" or p.username or p.password or p.port not in (None, 443)
                or p.fragment or p.query):
            raise Excluded("Invalid source URL")
        if url in self.excluded or url not in self.allowed:
            raise Excluded("URL excluded or absent from reviewed catalog")
        if p.hostname not in {"github.com", "raw.githubusercontent.com", "api.github.com", "odoo.com", "www.odoo.com", "oca.github.io"}:
            raise Excluded("Unknown source host")
        self.content(unquote(url))

    def content(self, text):
        # Inputs: text.
        # Does: Screen decoded content for excluded OCA sources.
        # Output: Successful validation or an exclusion error.
        text = unescape(unquote(text)).lower()
        if self.pattern.search(text):
            raise Excluded("OCA addon identifier detected; entire unit excluded")
        if any(re.search(r"(?<![\w.-])" + re.escape(repo) + r"(?![\w.-])", text) for repo in self.repos):
            raise Excluded("OCA addon repository detected; entire unit excluded")
