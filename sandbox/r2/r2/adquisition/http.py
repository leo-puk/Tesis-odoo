"""HTTPS transport with bounded retries; capture content stays in memory until admission."""
import json
import os
import time
from urllib import request, error, parse
from uuid import uuid4
from pathlib import Path
from .provenance import save, utcnow


class SameHostRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect requires a separately reviewed explicit URL')


class HttpCapture:
    def __init__(self, directory, transport=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.transport = transport or request.build_opener(SameHostRedirect()).open

    def get(self, url, projection=None, *, accept='application/vnd.github+json', persist=False):
        parsed = parse.urlparse(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password or any(
                k.lower() in {'token','access_token','key'} for k,_ in parse.parse_qsl(parsed.query)):
            raise ValueError('Only HTTPS URLs without credentials are accepted')
        headers={'User-Agent':'odoo-migration-r2/1.0','Accept':accept}
        if parsed.hostname=='api.github.com':
            headers['X-GitHub-Api-Version']='2022-11-28'
            token=os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
            if token: headers['Authorization']='Bearer '+token
        for attempt in range(3):
            try:
                with self.transport(request.Request(url,headers=headers),timeout=30) as response:
                    raw=response.read()
                    status=getattr(response,'status',200)
                    safe={k.lower():v for k,v in response.headers.items() if k.lower() in
                          {'content-type','etag','link','x-ratelimit-remaining','retry-after'}}
                if status != 200:
                    raise ValueError(f'Incomplete HTTP response: {status}')
                break
            except error.HTTPError as exc:
                if exc.code in {429,500,502,503,504} and attempt<2:
                    time.sleep(attempt+1)
                    continue
                raise ValueError(f'HTTP {exc.code}; capture not completed') from None
            except (error.URLError,TimeoutError):
                if attempt<2:
                    time.sleep(attempt+1)
                    continue
                raise ValueError('Network unavailable; capture not completed') from None
        value=projection(json.loads(raw)) if projection else raw
        record=dict(id=uuid4().hex,url=url,captured_at=utcnow(),status=status,headers=safe)
        if persist:
            raise ValueError('Persistence belongs to capture_plan after source admission')
        return value,record
