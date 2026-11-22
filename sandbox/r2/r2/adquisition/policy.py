"""Fixed, deterministic admission rules. Unknown URLs are denied."""
import re
from html import unescape
from urllib.parse import urlparse, unquote


class Excluded(ValueError):
    pass


class SourcePolicy:
    SHA_TOKEN = re.compile(r"\b[0-9a-f]{12,40}\b", re.I)
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
        self.exclude_pull_requests = catalog.get("exclude_pull_requests", False)
        shas = catalog.get("reference_shas", [])
        if type(self.exclude_pull_requests) is not bool or not isinstance(shas, list) or any(
                not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha, re.I) for sha in shas):
            raise ValueError("Invalid pull request exclusion policy or reference SHA list")
        self.reference_shas = {sha[:12].lower() for sha in shas}

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
        if self.exclude_pull_requests and p.hostname in {"github.com", "api.github.com"} and re.match(
                r"/(?:repos/)?[^/]+/[^/]+/(?:pulls?|commits?)(?:/|$)", unquote(p.path), re.I):
            raise Excluded("Individual PR and commit sources are excluded from the evaluation corpus")
        self.content(unquote(url))

    def content(self, text):
        # Inputs: text.
        # Does: Screen decoded content for excluded OCA sources.
        # Output: Successful validation or an exclusion error.
        text = unescape(unquote(text)).lower()
        self.reference_content(text)
        if self.pattern.search(text):
            raise Excluded("OCA addon identifier detected; entire unit excluded")
        if any(re.search(r"(?<![\w.-])" + re.escape(repo) + r"(?![\w.-])", text) for repo in self.repos):
            raise Excluded("OCA addon repository detected; entire unit excluded")

    def reference_content(self, text):
        """Reject explicit reference SHAs while preserving shared technical vocabulary."""
        if self.reference_shas and any(match[0][:12].lower() in self.reference_shas
                                       for match in self.SHA_TOKEN.finditer(text)):
            raise Excluded("Archived MIG/FIX reference SHA detected")
