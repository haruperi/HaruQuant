from __future__ import annotations

from backend.agents.chat.ai_chat.page_retrieval import PageSemanticRetrievalService


def test_page_semantic_retrieval_prioritizes_metric_table_chunks() -> None:
    service = PageSemanticRetrievalService()

    chunks = service.retrieve(
        dom_snapshot={
            "title": "Overview",
            "semantic_blocks": [
                {
                    "id": "metric-grid:overview",
                    "blockType": "metric_table",
                    "title": "Overview metrics",
                    "summary": "Performance metrics for all, long, and short trades.",
                    "rows": [
                        ["Net Profit", "$340.75", "$623.48", "($282.73)"],
                        ["Max Drawdown", "$280.44", "$191.13", "$376.89"],
                    ],
                },
                {
                    "id": "chart:drawdown",
                    "blockType": "chart",
                    "title": "Drawdown curve",
                    "summary": "Drawdown over time.",
                    "series": [
                        {
                            "label": "All Trades",
                            "points": [
                                {"x": "2026-01-10", "y": "0.4"},
                                {"x": "2026-02-03", "y": "2.77"},
                            ],
                        }
                    ],
                },
            ],
        },
        query="What is the max drawdown?",
    )

    assert chunks
    assert chunks[0].block_type == "metric_table"
    assert "max drawdown" in chunks[0].content.lower()


def test_page_semantic_retrieval_surfaces_chart_dates_for_time_queries() -> None:
    service = PageSemanticRetrievalService()

    chunks = service.retrieve(
        dom_snapshot={
            "title": "Drawdown",
            "semantic_blocks": [
                {
                    "id": "chart:drawdown",
                    "blockType": "chart",
                    "title": "Drawdown curve",
                    "summary": "Drawdown over time.",
                    "keywords": ["max drawdown", "date"],
                    "series": [
                        {
                            "label": "All Trades",
                            "points": [
                                {"x": "2026-01-10", "y": "0.4"},
                                {"x": "2026-02-03", "y": "2.77"},
                            ],
                        }
                    ],
                }
            ],
        },
        query="What date was the max drawdown?",
    )

    assert chunks
    assert chunks[0].block_type == "chart"
    assert "2026-02-03" in chunks[0].content


def test_page_semantic_retrieval_tracks_latest_and_previous_numeric_points() -> None:
    service = PageSemanticRetrievalService()

    chunks = service.retrieve(
        dom_snapshot={
            "title": "Equity",
            "semantic_blocks": [
                {
                    "id": "chart:equity",
                    "blockType": "chart",
                    "title": "Equity curve",
                    "summary": "Equity over time.",
                    "series": [
                        {
                            "label": "Equity",
                            "points": [
                                {"x": "2026-02-01", "y": "10100"},
                                {"x": "2026-02-02", "y": "10250"},
                                {"x": "2026-02-03", "y": "10340"},
                            ],
                        }
                    ],
                }
            ],
        },
        query="Compare current equity to the previous point",
    )

    assert chunks
    series = chunks[0].metadata["series"]["equity"]
    assert series["latest_x"] == "2026-02-03"
    assert series["previous_x"] == "2026-02-02"
    assert series["delta_numeric"] == 90.0
