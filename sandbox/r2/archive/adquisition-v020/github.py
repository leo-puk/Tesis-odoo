"""GitHub REST metadata only: no solution patches or review bodies."""
import re
from urllib import parse
from .http import HttpCapture
from .provenance import utcnow


class GitHubMetadata:
    def __init__(self, directory, transport=None):
        self.http = HttpCapture(directory, transport)

    def pages(self, path, projection):
        url = "https://api.github.com" + path
        seen = set()
        while url:
            if url in seen or parse.urlparse(url).hostname != "api.github.com":
                raise ValueError("Invalid pagination link")
            seen.add(url)
            value, record = self.http.get(url, projection)
            yield value, record
            link = record["headers"].get("link", "")
            match = re.search(r'<([^>]+)>; rel="next"', link)
            url = match.group(1) if match else None

    def search(self, query):
        path = "/search/issues?" + parse.urlencode(dict(q=query, per_page=100, sort="created", order="asc"))
        result, captures = [], []
        for page, capture in self.pages(path, lambda x: {
                "total_count": x["total_count"], "incomplete_results": x.get("incomplete_results", False),
                "items": [{**{k: i.get(k) for k in ("number", "title", "html_url", "created_at", "closed_at", "repository_url", "pull_request")},
                           "author": i.get("user", {}).get("login")} for i in x["items"]]}):
            if page["total_count"] > 1000 or page["incomplete_results"]:
                raise ValueError("Search is incomplete/over 1000; partition the query by repository/date before selection")
            result.extend(page["items"])
            captures.append(capture)
        return dict(query=query, extracted_at=utcnow(), items=result, captures=captures)

    def pull(self, repository, number):
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository) or int(number) < 1:
            raise ValueError("Invalid repository/pull number")
        path = f"/repos/{repository}/pulls/{int(number)}"
        def project(pr):
            return {**{k: pr.get(k) for k in ("number", "title", "html_url", "state", "created_at", "updated_at", "closed_at", "merged_at", "merge_commit_sha", "changed_files")},
                    "author": pr["user"]["login"], "base": {k: pr["base"].get(k) for k in ("ref", "sha")},
                    "head": {k: pr["head"].get(k) for k in ("ref", "sha")}}
        pr, capture = self.http.get("https://api.github.com"+path, project)
        reviews, files, captures = [], [], [capture]
        for values, rec in self.pages(path+"/reviews?per_page=100", lambda rows: [
                {"reviewer": r["user"]["login"], **{k: r.get(k) for k in ("id", "state", "submitted_at", "commit_id", "html_url", "author_association")}} for r in rows]):
            reviews.extend(values); captures.append(rec)
        for values, rec in self.pages(path+"/files?per_page=100", lambda rows: [
                {k: r.get(k) for k in ("filename", "status", "additions", "deletions", "sha")} for r in rows]):
            files.extend(values); captures.append(rec)
        if pr.get("changed_files") is not None and len(files) != pr["changed_files"]:
            raise ValueError("GitHub file list is incomplete; do not use this PR for audited selection")
        return dict(case_id=f"{repository}#{number}", repository=repository, pull=pr, reviews=reviews,
                    files=files, extracted_at=utcnow(), captures=captures,
                    maintainer_status="requires_identity_evidence_not_inferred_from_approval",
                    criteria_status="requires_six_criteria_review")
