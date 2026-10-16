"""Read-only source lookup tool with contract, authorization and timeout."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass

class ToolTimeout(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceLookupRequest:
    user_id: str
    resource_owner_id: str
    query: str
    pages: list[dict]
    max_results: int = 3


@dataclass(frozen=True)
class SourceLookupResult:
    status: str
    passages: list[dict]


class SourceLookupTool:
    name = "lookup_source"

    def __init__(self, timeout_seconds: float = 1.0):
        self.timeout_seconds = timeout_seconds

    def run(self, request: SourceLookupRequest) -> SourceLookupResult:
        # The application passes both identities; the tool re-checks them and
        # exposes no mutating action even if an LLM invents extra arguments.
        if not request.user_id or request.user_id != request.resource_owner_id:
            return SourceLookupResult("tool_forbidden", [])
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self._lookup, request)
            try:
                return future.result(timeout=self.timeout_seconds)
            except FutureTimeout as exc:
                future.cancel()
                raise ToolTimeout("source lookup timed out") from exc

    @staticmethod
    def _lookup(request: SourceLookupRequest) -> SourceLookupResult:
        terms = {term.lower() for term in request.query.split() if len(term) > 2}
        ranked = []
        for page in request.pages:
            text = str(page.get("text", ""))
            score = sum(term in text.lower() for term in terms)
            ranked.append((score, page))
        ranked.sort(key=lambda item: item[0], reverse=True)
        passages = [
            {"page": page["page"], "text": str(page["text"])[:4000]}
            for score, page in ranked[: max(1, min(request.max_results, 5))]
            if score > 0 or not terms
        ]
        return SourceLookupResult("ok", passages)
