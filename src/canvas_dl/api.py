from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from .utils import parse_link_header


class CanvasAPIError(Exception):
    pass


@dataclass
class CanvasClient:
    base_url: str
    access_token: str

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
        }

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.5, max=10.0),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _request(self, method: str, url: str, params: Optional[dict] = None) -> httpx.Response:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.request(method, url, headers=self._headers(), params=params)
        # Handle rate limiting
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "1"))
            time.sleep(min(retry_after, 10.0))
            raise httpx.HTTPError("rate limited")
        # Handle auth errors and others
        if resp.status_code >= 400:
            message = f"HTTP {resp.status_code}: {resp.text[:500]}"
            raise CanvasAPIError(message)
        return resp

    def _paginate(self, path: str, params: Optional[dict] = None) -> List[dict]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        collected: List[dict] = []
        next_url: Optional[str] = url
        while next_url:
            resp = self._request("GET", next_url, params=params if next_url == url else None)
            try:
                data = resp.json()
                if isinstance(data, list):
                    collected.extend(data)
                else:
                    collected.append(data)
            except Exception:
                break
            links = parse_link_header(resp.headers.get("Link"))
            next_url = links.get("next")
        return collected

    # High-level endpoints
    def list_courses(self, enrollment_state: Optional[str] = None, published: Optional[bool] = None) -> List[dict]:
        params: Dict[str, Any] = {"per_page": 100}
        if enrollment_state:
            params["enrollment_state"] = enrollment_state
        if published is not None:
            params["published"] = str(published).lower()
        return self._paginate("/courses", params=params)

    def list_modules(self, course_id: int) -> List[dict]:
        params = {"per_page": 100, "include[]": "items"}
        return self._paginate(f"/courses/{course_id}/modules", params=params)

    def list_module_items(self, course_id: int, module_id: int) -> List[dict]:
        params = {"per_page": 100}
        return self._paginate(f"/courses/{course_id}/modules/{module_id}/items", params=params)

    def get_file_info(self, file_id: int) -> dict:
        url = f"{self.base_url.rstrip('/')}/files/{file_id}"
        resp = self._request("GET", url)
        return resp.json()
