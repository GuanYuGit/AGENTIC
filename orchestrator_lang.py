#!/usr/bin/env python3
"""
Experimental Orchestrator using LangChain + LangGraph

Workflow:
1) Scraper runs first.
2) Wiki Fact Checker, Fake News Agent, and Image Evaluator run in parallel.
3) Aggregator runs last.
"""

import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

from langchain.tools import tool
from langgraph.graph import StateGraph
from collections.abc import Mapping


PROJECT_ROOT = Path("/Users/wongk/Desktop/simplyN/AGENTIC")


def run_subprocess(script: Path, *args) -> Dict[str, Any]:
    """Helper to run a script via subprocess and capture results."""
    completed = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


# Wrap each existing agent as a LangChain tool
@tool("scraper")
def run_scraper(url: str) -> Dict[str, Any]:
    """Scrape the given URL and return raw JSON output."""
    return run_subprocess(PROJECT_ROOT / "scrapers.py", url)


@tool("wiki_checker")
def run_wiki_checker(_: str) -> Dict[str, Any]:
    """Run Wikipedia fact checker on scraped data."""
    return run_subprocess(PROJECT_ROOT / "wiki_fact_checker.py")


@tool("fake_news")
def run_fake_news(_: str) -> Dict[str, Any]:
    """Analyze scraped text for fake news patterns."""
    return run_subprocess(PROJECT_ROOT / "fake_news_agent.py")


@tool("image_eval")
def run_image_eval(_: str) -> Dict[str, Any]:
    """Evaluate scraped images for authenticity/relevance."""
    return run_subprocess(PROJECT_ROOT / "kk" / "agent_tester.py")


@tool("aggregator")
def run_ai(_: str) -> Dict[str, Any]:
    """Aggregate all results into final news validity summary."""
    return run_subprocess(PROJECT_ROOT / "AI.py")


def build_graph():
    """Build LangGraph workflow with state schema."""

    state_schema = {
        "scraper": DictType,
        "wiki": DictType,
        "fake_news": DictType,
        "image_eval": DictType,
        "aggregator": DictType,
    }


    graph = StateGraph(state_schema=state_schema)

    # Add nodes
    graph.add_node("scraper", run_scraper)
    graph.add_node("wiki", run_wiki_checker)
    graph.add_node("fake_news", run_fake_news)
    graph.add_node("image_eval", run_image_eval)
    graph.add_node("aggregator", run_ai)

    # Workflow edges
    graph.add_edge("scraper", "wiki")
    graph.add_edge("scraper", "fake_news")
    graph.add_edge("scraper", "image_eval")
    graph.add_edge(["wiki", "fake_news", "image_eval"], "aggregator")

    return graph.compile()


def main():
    # Prompt for URL
    if len(sys.argv) > 1:
        url = sys.argv[1].strip()
    else:
        url = input("Enter a URL to analyze: ").strip()

    if not url.startswith("http"):
        print("Please enter a valid URL starting with http or https.")
        sys.exit(1)

    executor = build_graph()

    # Run the workflow
    print("Starting LangGraph workflow...")
    results = executor.invoke({"scraper": url})

    print("\n=== Workflow Results ===")
    for step, output in results.items():
        print(f"\n[{step.upper()}]")
        print(output)

    print("\nDone.")


if __name__ == "__main__":
    main()

class DictType:
    pass