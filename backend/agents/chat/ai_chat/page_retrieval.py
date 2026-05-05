"""Current-page semantic chunking and retrieval for AI chat."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable


@dataclass(frozen=True)
class RetrievedPageChunk:
    chunk_id: str
    block_type: str
    title: str
    content: str
    score: float
    metadata: dict[str, object] = field(default_factory=dict)


class PageSemanticRetrievalService:
    """Retrieve the most relevant current-page semantic chunks for a prompt."""

    def retrieve(self, *, dom_snapshot: dict[str, object] | None, query: str, top_k: int = 4) -> list[RetrievedPageChunk]:
        if not isinstance(dom_snapshot, dict):
            return []
        chunks = list(self._build_chunks(dom_snapshot))
        if not chunks:
            return []
        scored: list[RetrievedPageChunk] = []
        for chunk in chunks:
            score = self._score_chunk(query=query, chunk=chunk)
            if score <= 0:
                continue
            scored.append(
                RetrievedPageChunk(
                    chunk_id=str(chunk["chunk_id"]),
                    block_type=str(chunk["block_type"]),
                    title=str(chunk["title"]),
                    content=str(chunk["content"]),
                    score=score,
                    metadata=chunk.get("metadata", {}) if isinstance(chunk.get("metadata"), dict) else {},
                )
            )
        if not scored:
            return []
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def _build_chunks(self, dom_snapshot: dict[str, object]) -> Iterable[dict[str, object]]:
        title = str(dom_snapshot.get("title") or "Current page").strip()
        semantic_blocks = dom_snapshot.get("semantic_blocks")
        if isinstance(semantic_blocks, list):
            for index, block in enumerate(semantic_blocks):
                if not isinstance(block, dict):
                    continue
                block_id = str(block.get("id") or f"semantic_{index}")
                block_type = str(block.get("blockType") or block.get("block_type") or "semantic")
                block_title = str(block.get("title") or f"{title} {block_type}").strip()
                content, metadata = self._serialize_semantic_block(block)
                if content:
                    yield {
                        "chunk_id": block_id,
                        "block_type": block_type,
                        "title": block_title,
                        "content": content,
                        "metadata": metadata,
                    }

        tables = dom_snapshot.get("tables")
        if isinstance(tables, list):
            for index, table in enumerate(tables):
                if not isinstance(table, dict):
                    continue
                headers = table.get("headers") if isinstance(table.get("headers"), list) else []
                rows = table.get("rows") if isinstance(table.get("rows"), list) else []
                row_lines = []
                row_map: dict[str, list[str]] = {}
                for row in rows[:10]:
                    if isinstance(row, list):
                        row_text = " | ".join(str(cell) for cell in row[:6])
                        row_lines.append(row_text)
                        if row and str(row[0]).strip():
                            row_map[str(row[0]).strip().lower()] = [str(cell).strip() for cell in row[1:6]]
                content = " ".join(
                    part for part in (
                        headers and f"Columns: {', '.join(str(header) for header in headers[:6])}",
                        row_lines and f"Rows: {' ; '.join(row_lines[:8])}",
                    ) if part
                )
                if content:
                    yield {
                        "chunk_id": f"dom_table_{index}",
                        "block_type": "table",
                        "title": f"{title} table {index + 1}",
                        "content": content,
                        "metadata": {
                            "headers": [str(header) for header in headers[:8]],
                            "row_map": row_map,
                        },
                    }

        excerpt = str(dom_snapshot.get("text_excerpt") or "").strip()
        if excerpt:
            yield {
                "chunk_id": "dom_text_excerpt",
                "block_type": "text",
                "title": f"{title} excerpt",
                "content": excerpt,
                "metadata": {},
            }

    def _serialize_semantic_block(self, block: dict[str, object]) -> tuple[str, dict[str, object]]:
        parts: list[str] = []
        metadata: dict[str, object] = {}
        summary = str(block.get("summary") or "").strip()
        if summary:
            parts.append(summary)

        keywords = block.get("keywords")
        if isinstance(keywords, list) and keywords:
            parts.append("Keywords: " + ", ".join(str(keyword) for keyword in keywords[:12]))

        metrics = block.get("metrics")
        if isinstance(metrics, list) and metrics:
            metric_parts = []
            metric_map: dict[str, str] = {}
            for metric in metrics[:12]:
                if isinstance(metric, dict):
                    label = str(metric.get("label") or "").strip()
                    value = str(metric.get("value") or "").strip()
                    if label and value:
                        metric_parts.append(f"{label}: {value}")
                        metric_map[label.lower()] = value
            if metric_parts:
                parts.append("Metrics: " + " ; ".join(metric_parts))
                metadata["metrics"] = metric_map

        headers = block.get("headers")
        if isinstance(headers, list) and headers:
            header_values = [str(header) for header in headers[:8]]
            parts.append("Columns: " + ", ".join(header_values))
            metadata["headers"] = header_values

        rows = block.get("rows")
        if isinstance(rows, list) and rows:
            row_parts = []
            row_map: dict[str, list[str]] = {}
            for row in rows[:12]:
                if isinstance(row, list):
                    row_text = " | ".join(str(cell) for cell in row[:6])
                    row_parts.append(row_text)
                    if row and str(row[0]).strip():
                        row_map[str(row[0]).strip().lower()] = [str(cell).strip() for cell in row[1:6]]
            if row_parts:
                parts.append("Rows: " + " ; ".join(row_parts[:8]))
                metadata["row_map"] = row_map

        series = block.get("series")
        if isinstance(series, list) and series:
            series_parts = []
            series_metadata: dict[str, dict[str, object]] = {}
            for series_item in series[:6]:
                if not isinstance(series_item, dict):
                    continue
                label = str(series_item.get("label") or "Series").strip()
                points = series_item.get("points") if isinstance(series_item.get("points"), list) else []
                if not points:
                    continue
                serialized_points, one_series_metadata = self._summarize_series(label=label, points=points)
                if serialized_points:
                    series_parts.append(serialized_points)
                if one_series_metadata:
                    series_metadata[label.lower()] = one_series_metadata
            if series_parts:
                parts.append("Series: " + " ; ".join(series_parts))
                metadata["series"] = series_metadata

        return " ".join(part for part in parts if part).strip(), metadata

    def _summarize_series(self, *, label: str, points: list[object]) -> tuple[str, dict[str, object]]:
        normalized_points: list[dict[str, object]] = []
        numeric_points: list[dict[str, float | str]] = []
        for point in points[:160]:
            if not isinstance(point, dict):
                continue
            x_value = str(point.get("x") or "").strip()
            y_value = str(point.get("y") or "").strip()
            if not x_value or not y_value:
                continue
            normalized_points.append({"x": x_value, "y": y_value})
            numeric_value = self._parse_number(y_value)
            if numeric_value is not None:
                numeric_points.append({"x": x_value, "y": numeric_value})

        if not normalized_points:
            return "", {}

        first_point = normalized_points[0]
        last_point = normalized_points[-1]
        point_text = f"{label} from {first_point['x']}={first_point['y']} to {last_point['x']}={last_point['y']}"

        metadata: dict[str, object] = {
            "latest_x": last_point["x"],
            "latest_y": last_point["y"],
            "first_x": first_point["x"],
            "first_y": first_point["y"],
        }

        if len(normalized_points) <= 10:
            point_text += " (" + ", ".join(f"{point['x']}={point['y']}" for point in normalized_points) + ")"

        if numeric_points:
            latest_numeric = numeric_points[-1]
            metadata["latest_numeric"] = latest_numeric["y"]
            if len(numeric_points) >= 2:
                previous_numeric = numeric_points[-2]
                metadata["previous_x"] = previous_numeric["x"]
                metadata["previous_numeric"] = previous_numeric["y"]
                metadata["delta_numeric"] = float(latest_numeric["y"]) - float(previous_numeric["y"])
            min_point = min(numeric_points, key=lambda item: float(item["y"]))
            max_point = max(numeric_points, key=lambda item: float(item["y"]))
            metadata["min_x"] = min_point["x"]
            metadata["min_numeric"] = min_point["y"]
            metadata["max_x"] = max_point["x"]
            metadata["max_numeric"] = max_point["y"]
            point_text += (
                f". Latest {latest_numeric['x']}={latest_numeric['y']},"
                f" min {min_point['x']}={min_point['y']},"
                f" max {max_point['x']}={max_point['y']}"
            )

        return point_text, metadata

    @staticmethod
    def _parse_number(value: str) -> float | None:
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None

    def _score_chunk(self, *, query: str, chunk: dict[str, object]) -> float:
        query_terms = set(re.findall(r"[a-z0-9%]+", query.lower()))
        if not query_terms:
            return 0.0
        normalized_query = query.lower()
        haystack = f"{chunk['title']} {chunk['content']}".lower()
        haystack_terms = set(re.findall(r"[a-z0-9%]+", haystack))
        overlap = len(query_terms & haystack_terms)
        broad_summary_query = any(
            phrase in normalized_query
            for phrase in ("summary", "summarise", "summarize", "current page", "this page", "results")
        )
        if overlap == 0 and not broad_summary_query:
            return 0.0
        score = overlap * 5.0
        if broad_summary_query:
            score += 3.0

        direct_phrases = (
            "max drawdown",
            "net profit",
            "total return",
            "cagr",
            "profit factor",
            "win rate",
            "expectancy",
            "sharpe",
            "sortino",
            "calmar",
            "value at risk",
            "drawdown",
            "equity",
            "pnl",
            "date",
            "latest",
            "current",
            "previous",
            "compare",
            "bullish",
            "bearish",
        )
        for phrase in direct_phrases:
            if phrase in normalized_query and phrase in haystack:
                score += 8.0

        metadata = chunk.get("metadata", {}) if isinstance(chunk.get("metadata"), dict) else {}
        if any(term in normalized_query for term in ("date", "when")) and metadata.get("series"):
            score += 4.0
        if any(term in normalized_query for term in ("compare", "previous")) and metadata.get("series"):
            score += 4.0
        if any(term in normalized_query for term in ("latest", "current", "last")) and metadata.get("series"):
            score += 3.0
        if str(chunk["block_type"]) in {"metric_table", "chart"}:
            score += 2.0
        return score
