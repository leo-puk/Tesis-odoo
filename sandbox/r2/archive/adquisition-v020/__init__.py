"""Internet source collection for R2 (adquisition)."""
from .github import GitHubMetadata
from .http import HttpCapture
from .sources import capture_plan

__all__ = ["GitHubMetadata", "HttpCapture", "capture_plan"]
