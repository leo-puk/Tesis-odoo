"""HTTPS capture transport with bounded retries and auditable records."""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import request, error, parse
from .provenance import save, sha, utcnow


class SameHostRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if parse.urlparse(req.full_url).hostname != parse.urlparse(newurl).hostname:
            raise ValueError("Cross-host redirects require a new explicit source URL")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HttpCapture:
    def __init__(self, directory, transport=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.transport = transport or request.build_opener(SameHostRedirect()).open

    def get(self, url, projection=None):
        parsed = parse.urlparse(url)
        if parsed.scheme != "https" or parsed.username or parsed.password or any(
                k.lower() in {"token", "access_token", "key"} for k, _ in parse.parse_qsl(parsed.query)):
            raise ValueError("Only HTTPS source URLs without credentials are accepted")
        headers = {"User-Agent": "odoo-migration-r2/0.2", "Accept": "application/vnd.github+json"}
        if parsed.hostname == "api.github.com":
            headers["X-GitHub-Api-Version"] = "2022-11-28"
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            if token:
                headers["Authorization"] = "Bearer " + token
        for attempt in range(3):
            try:
                with self.transport(request.Request(url, headers=headers), timeout=30) as response:
                    raw = response.read()
                    status = getattr(response, "status", 200)
                    safe_headers = {k.lower(): v for k, v in response.headers.items()
                                    if k.lower() in {"content-type", "etag", "link", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"}}
                break
            except error.HTTPError as exc:
                if exc.code in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(1 + attempt)
                    continue
                # Do not log request headers or token-bearing exception payloads.
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
                save(self.directory / f"error-{sha(url.encode())[:16]}-{stamp}.json",
                     dict(url=url, captured_at=utcnow(), status=exc.code,
                          headers={k.lower(): v for k, v in exc.headers.items() if k.lower() in
                                   {"x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset", "retry-after"}},
                          reason="HTTP error; rate limits/authentication may require retry later"))
                raise ValueError(f"HTTP {exc.code} for {parsed.hostname}{parsed.path}") from None
            except (error.URLError, TimeoutError):
                raise ValueError(f"Network unavailable for {parsed.hostname}{parsed.path}") from None
        captured = utcnow()
        original_hash = sha(raw)
        key = sha(url.encode())[:20]
        if projection is not None:
            value = projection(json.loads(raw))
            stored = json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
            original_path = self.directory / f"{key}-{sha(stored)[:12]}.json"
            original_path.write_bytes(stored)
            form = "projected_metadata_only_no_code_or_review_bodies"
        else:
            value = raw
            original_path = self.directory / f"{key}-{original_hash[:12]}.bin"
            original_path.write_bytes(raw)
            form = "original_bytes"
        record = dict(url=url, captured_at=captured, status=status, response_sha256=original_hash,
                      stored_sha256=sha(original_path.read_bytes()), stored_file=str(original_path.resolve()),
                      capture_form=form, headers=safe_headers)
        save(self.directory / f"{key}.capture.json", record)
        return value, record
