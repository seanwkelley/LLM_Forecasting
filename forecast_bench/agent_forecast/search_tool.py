"""Abstracted web-search tool for the agent-forecast pipeline.

Prefers Tavily (purpose-built for LLM agents, returns cleaner snippets).
Falls back to Serper (Google results via SerpAPI-compatible endpoint) if Tavily
is unavailable.

Each `search(query, max_results)` call returns a list of dicts:
    [{"title": ..., "url": ..., "snippet": ..., "published": ...?}]
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import requests

from forecast_bench.agent_forecast.config import (
    MAX_RESULTS_PER_QUERY, SEARCH_SNIPPET_CHARS,
    get_serper_key, get_tavily_key,
)


@dataclass
class SearchCall:
    query: str
    results: list[dict] = field(default_factory=list)
    tool: str = ""
    latency_ms: int = 0


class SearchTool:
    """Web search with a uniform return shape across providers."""

    def __init__(self, prefer: str = "tavily"):
        self.prefer = prefer
        self._tavily = get_tavily_key()
        self._serper = get_serper_key()
        if not (self._tavily or self._serper):
            raise RuntimeError(
                "No search API key found. Set TAVILY_API_KEY or SERPER_API_KEY.")
        self.history: list[SearchCall] = []

    def search(self, query: str,
               max_results: int = MAX_RESULTS_PER_QUERY) -> SearchCall:
        t0 = time.time()
        order = ["tavily", "serper"] if self.prefer == "tavily" else ["serper", "tavily"]

        last_err = None
        for tool in order:
            try:
                if tool == "tavily" and self._tavily:
                    results = self._tavily_search(query, max_results)
                elif tool == "serper" and self._serper:
                    results = self._serper_search(query, max_results)
                else:
                    continue
                call = SearchCall(query=query, results=results, tool=tool,
                                  latency_ms=int((time.time() - t0) * 1000))
                self.history.append(call)
                return call
            except Exception as e:
                last_err = e
                continue
        # All tools failed
        call = SearchCall(query=query, results=[], tool="failed",
                          latency_ms=int((time.time() - t0) * 1000))
        self.history.append(call)
        if last_err:
            print(f"[search] all providers failed: {last_err}")
        return call

    # ── Provider-specific wrappers ─────────────────────────────────────────

    def _tavily_search(self, query: str, max_results: int) -> list[dict]:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": self._tavily,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": False,
            },
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        results = []
        for item in data.get("results", []):
            snippet = (item.get("content") or "")[:SEARCH_SNIPPET_CHARS]
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": snippet,
                "published": item.get("published_date"),
            })
        return results

    def _serper_search(self, query: str, max_results: int) -> list[dict]:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": self._serper, "Content-Type": "application/json"},
            json={"q": query, "num": max_results},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        results = []
        for item in data.get("organic", [])[:max_results]:
            snippet = (item.get("snippet") or "")[:SEARCH_SNIPPET_CHARS]
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": snippet,
                "published": item.get("date"),
            })
        return results

    def reset(self):
        self.history.clear()
