"""
Ethical and Robust HTTP Fetcher module.
Adheres strictly to web etiquette:
- Identifies project clearly via custom User-Agent.
- Enforces polite rate limiting per domain.
- Verifies robots.txt compliance before requests.
- Caches responses locally to prevent duplicate requests.
- Handles HTTP 429 with bounded backoff and stops on HTTP 403.
- Strictly NO proxies or identity-spoofing to bypass blocks.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from src.config import (
    CACHE_DIR,
    DEFAULT_DELAY,
    LOGS_DIR,
    MAX_RETRIES,
    BACKOFF_FACTOR,
    REQUEST_TIMEOUT,
    USER_AGENT,
)

logger = logging.getLogger("Fetcher")


class FetchError(Exception):
    """Base exception for fetch errors."""
    pass


class RobotsDisallowedError(FetchError):
    """Raised when access is forbidden by robots.txt."""
    pass


class RateLimitExceededError(FetchError):
    """Raised when encountering repeated HTTP 429."""
    pass


class ForbiddenAccessError(FetchError):
    """Raised when server returns HTTP 403 Forbidden."""
    pass


@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int
    content: bytes
    text: str
    content_type: str
    headers: Dict[str, str]
    fetched_at_utc: str
    sha256: str
    from_cache: bool
    is_robots_allowed: bool = True

    def json(self) -> Any:
        return json.loads(self.text)


class PoliteFetcher:
    """
    HTTP client configured for polite, reproducible scraping with disk caching,
    per-domain rate limiting, and robots.txt parsing.
    """

    def __init__(
        self,
        user_agent: str = USER_AGENT,
        timeout: int = REQUEST_TIMEOUT,
        delay: float = DEFAULT_DELAY,
        cache_dir: Path = CACHE_DIR,
        max_retries: int = MAX_RETRIES,
        backoff_factor: float = BACKOFF_FACTOR,
        check_robots: bool = True,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.delay = delay
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.check_robots_flag = check_robots

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

        self._last_request_time: Dict[str, float] = {}
        self._robot_parsers: Dict[str, RobotFileParser] = {}

    def _get_domain(self, url: str) -> str:
        """Extract netloc/domain from URL."""
        return urlparse(url).netloc.lower()

    def _wait_rate_limit(self, domain: str) -> None:
        """Sleep if required to maintain rate limit for domain."""
        if domain in self._last_request_time:
            elapsed = time.time() - self._last_request_time[domain]
            if elapsed < self.delay:
                sleep_time = self.delay - elapsed
                logger.debug(f"Rate limiting for {domain}: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        self._last_request_time[domain] = time.time()

    def get_robots_parser(self, url: str) -> RobotFileParser:
        """Fetch and cache RobotFileParser for URL's domain."""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        domain = parsed.netloc.lower()

        if domain in self._robot_parsers:
            return self._robot_parsers[domain]

        robots_url = f"{base_url}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)

        try:
            self._wait_rate_limit(domain)
            resp = self.session.get(robots_url, timeout=self.timeout)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
                logger.info(f"Loaded robots.txt for {domain} (200 OK)")
            elif resp.status_code in (401, 403):
                # Site denies robots file: conservative stance
                logger.warning(f"Robots.txt for {domain} returned {resp.status_code}; disallowing crawling.")
                rp.parse(["User-agent: *", "Disallow: /"])
            else:
                # 404 or others: standard convention is crawling is permitted
                logger.info(f"Robots.txt for {domain} returned {resp.status_code}; allowing default.")
                rp.parse(["User-agent: *", "Disallow:"])
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {domain}: {e}; defaulting to allow.")
            rp.parse(["User-agent: *", "Disallow:"])

        self._robot_parsers[domain] = rp
        return rp

    def is_allowed_by_robots(self, url: str) -> bool:
        """Check if URL can be fetched under robots.txt."""
        rp = self.get_robots_parser(url)
        return rp.can_fetch(self.user_agent, url)

    def _get_cache_paths(self, url: str) -> Tuple[Path, Path]:
        """Return (content_path, meta_path) for cached response."""
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        content_path = self.cache_dir / f"{url_hash}.bin"
        meta_path = self.cache_dir / f"{url_hash}.meta.json"
        return content_path, meta_path

    def _load_from_cache(self, url: str) -> Optional[FetchResult]:
        """Attempt to load response from local cache."""
        content_path, meta_path = self._get_cache_paths(url)
        if content_path.exists() and meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                with open(content_path, "rb") as f:
                    content = f.read()

                # Verify SHA-256 integrity
                content_sha = hashlib.sha256(content).hexdigest()
                if content_sha != meta.get("sha256"):
                    logger.warning(f"Cache checksum mismatch for {url}; discarding cache.")
                    return None

                # Guess encoding
                encoding = "utf-8"
                content_type = meta.get("content_type", "")
                if "charset=" in content_type:
                    encoding = content_type.split("charset=")[-1].split(";")[0].strip()

                text = content.decode(encoding, errors="replace")

                logger.debug(f"Cache HIT for {url}")
                return FetchResult(
                    url=url,
                    final_url=meta.get("final_url", url),
                    status_code=meta.get("status_code", 200),
                    content=content,
                    text=text,
                    content_type=content_type,
                    headers=meta.get("headers", {}),
                    fetched_at_utc=meta.get("fetched_at_utc", ""),
                    sha256=content_sha,
                    from_cache=True,
                    is_robots_allowed=True,
                )
            except Exception as e:
                logger.warning(f"Error reading cache for {url}: {e}")
                return None
        return None

    def _save_to_cache(
        self,
        url: str,
        final_url: str,
        status_code: int,
        content: bytes,
        headers: Dict[str, str],
        content_type: str,
        fetched_at_utc: str,
    ) -> str:
        """Save response to local cache."""
        content_path, meta_path = self._get_cache_paths(url)
        content_sha = hashlib.sha256(content).hexdigest()

        with open(content_path, "wb") as f:
            f.write(content)

        meta = {
            "url": url,
            "final_url": final_url,
            "status_code": status_code,
            "content_type": content_type,
            "headers": dict(headers),
            "fetched_at_utc": fetched_at_utc,
            "sha256": content_sha,
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        return content_sha

    def fetch(
        self,
        url: str,
        use_cache: bool = True,
        force_refresh: bool = False,
        enforce_robots: Optional[bool] = None,
    ) -> FetchResult:
        """
        Fetch URL with caching, robots checking, rate limiting, and 429/403 handling.
        """
        check_rob = self.check_robots_flag if enforce_robots is None else enforce_robots

        # Check robots.txt (unless explicitly skipped for robots.txt itself)
        if check_rob and not url.endswith("/robots.txt"):
            allowed = self.is_allowed_by_robots(url)
            if not allowed:
                msg = f"URL disallowed by robots.txt: {url}"
                logger.error(msg)
                raise RobotsDisallowedError(msg)

        # Check cache
        if use_cache and not force_refresh:
            cached = self._load_from_cache(url)
            if cached is not None:
                return cached

        # Perform network request with rate limiting and backoff
        domain = self._get_domain(url)
        retries = 0

        while True:
            self._wait_rate_limit(domain)
            logger.info(f"GET {url} (attempt {retries + 1}/{self.max_retries + 1})")

            try:
                resp = self.session.get(url, timeout=self.timeout)
            except requests.RequestException as e:
                logger.error(f"Request failed for {url}: {e}")
                raise FetchError(f"Network error accessing {url}: {e}") from e

            # Handle HTTP 403 Forbidden
            if resp.status_code == 403:
                msg = f"HTTP 403 Forbidden for {url}. Access is restricted; stopping request without retries."
                logger.critical(msg)
                raise ForbiddenAccessError(msg)

            # Handle HTTP 429 Too Many Requests
            if resp.status_code == 429:
                retries += 1
                if retries > self.max_retries:
                    msg = f"HTTP 429 Too Many Requests for {url}. Exceeded maximum retries ({self.max_retries}); aborting."
                    logger.critical(msg)
                    raise RateLimitExceededError(msg)

                # Check Retry-After header
                retry_after_hdr = resp.headers.get("Retry-After")
                if retry_after_hdr and retry_after_hdr.isdigit():
                    wait_sec = min(float(retry_after_hdr), 30.0)
                else:
                    wait_sec = (self.delay * (self.backoff_factor ** retries))

                logger.warning(f"HTTP 429 encountered for {url}. Backing off for {wait_sec:.1f}s...")
                time.sleep(wait_sec)
                continue

            # Success or other status codes
            fetched_at_utc = datetime.now(timezone.utc).isoformat()
            content = resp.content
            content_type = resp.headers.get("Content-Type", "")

            # Determine text
            encoding = resp.encoding or "utf-8"
            try:
                text = content.decode(encoding, errors="replace")
            except Exception:
                text = resp.text

            # Cache successful 200 responses
            content_sha = hashlib.sha256(content).hexdigest()
            if use_cache and resp.status_code == 200:
                self._save_to_cache(
                    url=url,
                    final_url=resp.url,
                    status_code=resp.status_code,
                    content=content,
                    headers=resp.headers,
                    content_type=content_type,
                    fetched_at_utc=fetched_at_utc,
                )

            return FetchResult(
                url=url,
                final_url=resp.url,
                status_code=resp.status_code,
                content=content,
                text=text,
                content_type=content_type,
                headers=dict(resp.headers),
                fetched_at_utc=fetched_at_utc,
                sha256=content_sha,
                from_cache=False,
                is_robots_allowed=True,
            )
