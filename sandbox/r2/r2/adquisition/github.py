"""GitHub REST collection. Public source URLs require explicit admission."""
import json
import re
from urllib import parse
from .http import HttpCapture
from .policy import Excluded


class Incomplete(ValueError):
    pass


class GitHubMetadata:
    def __init__(self, directory, transport=None, policy=None):
        # Inputs: directory, transport, policy.
        # Does: Configure GitHub retrieval and its acquisition context.
        # Output: A GitHub client instance.
        self.http = HttpCapture(directory, transport)
        self.policy = policy

    def _check(self, url):
        # Inputs: url.
        # Does: Apply the configured admission policy to the supplied URL.
        # Output: Successful validation or an exclusion error.
        if self.policy is None:
            raise ValueError("A reviewed source policy is required")
        self.policy.url(url)

    def _get(self, url, captures, accept="application/vnd.github+json"):
        # Inputs: url, captures, accept.
        # Does: Fetch a GitHub resource and record its admission and capture.
        # Output: Response bytes and an updated capture list.
        raw, record = self.http.get(url, accept=accept, persist=False)
        self.policy.content(raw.decode('utf-8'))
        captures.append(record)
        return raw

    def diff_bytes(self, url):
        # Inputs: url.
        # Does: Build and retrieve the official Odoo comparison request.
        # Output: Diff response bytes and capture records.
        self._check(url)
        p = parse.urlparse(url)
        prefix = '/repos/odoo/odoo/compare/' if p.hostname == 'api.github.com' else '/odoo/odoo/compare/'
        if p.hostname not in {'api.github.com', 'github.com'} or not p.path.startswith(prefix):
            raise Excluded('Only official Odoo comparison URLs accepted')
        comparison = p.path[len(prefix):]
        if not re.fullmatch(r'[\w./%+-]+\.\.\.[\w./%+-]+', comparison):
            raise ValueError('Expected BASE...HEAD comparison')
        captures = []
        raw = self._get('https://api.github.com/repos/odoo/odoo/compare/' + comparison,
                        captures, 'application/vnd.github.diff')
        return raw, captures

    def _pages(self, path, captures):
        # Construct pagination locally; never follow arbitrary links from content.
        # Inputs: path, captures.
        # Does: Collect GitHub resources page by page.
        # Output: The accumulated items or an incomplete-resource error.
        result = []
        for page in range(1, 1001):
            url = 'https://api.github.com' + path + f'?per_page=100&page={page}'
            values = json.loads(self._get(url, captures))
            if not isinstance(values, list):
                raise Incomplete('Unexpected paginated response')
            result.extend(values)
            if len(values) < 100:
                return result
        raise Incomplete('Pagination limit reached')

    def pull(self, url):
        # Inputs: url.
        # Does: Collect a merged pull request and its related resources.
        # Output: The PR bundle and capture records.
        self._check(url)
        match = re.fullmatch(r'https://github.com/([\w.-]+/[\w.-]+)/pull/([1-9]\d*)', url)
        if not match:
            raise ValueError('Expected a GitHub PR URL')
        repo, number = match.groups()
        path = f'/repos/{repo}/pulls/{number}'
        captures = []
        pr = json.loads(self._get('https://api.github.com' + path, captures))
        if not pr.get('merged_at'):
            raise Excluded('PR is not merged')
        files = self._pages(path + '/files', captures)
        commits = self._pages(path + '/commits', captures)
        if len(files) != pr.get('changed_files') or len(commits) != pr.get('commits'):
            raise Incomplete('GitHub file or commit listing is incomplete')
        result = dict(pull=pr, files=files, commits=commits,
            comments=self._pages(f'/repos/{repo}/issues/{number}/comments', captures),
            reviews=self._pages(path + '/reviews', captures),
            review_comments=self._pages(path + '/comments', captures),
            diff=self._get('https://api.github.com' + path, captures,
                           'application/vnd.github.diff').decode('utf-8'))
        return result, captures
