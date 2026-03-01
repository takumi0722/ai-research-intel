#!/usr/bin/env python3
"""NeurIPS / ICML / ICLR / ACL の論文情報を DBLP API から取得するスクリプト."""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DBLP_API_URL = "https://dblp.org/search/publ/api"

CONFERENCE_STREAMS = {
    "neurips": "streams/conf/nips:",
    "icml": "streams/conf/icml:",
    "iclr": "streams/conf/iclr:",
    "acl": "streams/conf/acl:",
}


@dataclass(slots=True)
class Paper:
    conference: str
    year: int
    title: str
    authors: list[str]
    venue: str
    url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "conference": self.conference,
            "year": self.year,
            "title": self.title,
            "authors": self.authors,
            "venue": self.venue,
            "url": self.url,
        }


def fetch_json(url: str, retries: int = 3, timeout: int = 30) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:  # noqa: BLE001 - API 通信の再試行制御
            last_error = error
            if attempt < retries:
                time.sleep(1.5 * attempt)

    assert last_error is not None
    raise RuntimeError(f"API リクエストに失敗しました: {url}\n{last_error}")


def build_query(stream: str, year: int) -> str:
    # DBLP query syntax: stream:<stream> AND year:<year>
    return f"stream:{stream} AND year:{year}"


def normalize_authors(author_data: Any) -> list[str]:
    if not author_data:
        return []

    authors_field = author_data.get("author") if isinstance(author_data, dict) else author_data
    if isinstance(authors_field, list):
        return [a.get("text", "").strip() if isinstance(a, dict) else str(a).strip() for a in authors_field if str(a).strip()]
    if isinstance(authors_field, dict):
        name = authors_field.get("text", "").strip()
        return [name] if name else []
    if isinstance(authors_field, str):
        text = authors_field.strip()
        return [text] if text else []

    return []


def fetch_papers_for_conference(
    conference: str,
    year: int,
    max_results: int,
    page_size: int,
) -> list[Paper]:
    stream = CONFERENCE_STREAMS[conference]
    query = build_query(stream, year)
    papers: list[Paper] = []

    offset = 0
    while len(papers) < max_results:
        params = {
            "q": query,
            "h": min(page_size, max_results - len(papers)),
            "f": offset,
            "format": "json",
        }
        url = f"{DBLP_API_URL}?{urllib.parse.urlencode(params)}"
        payload = fetch_json(url)

        hits_section = payload.get("result", {}).get("hits", {})
        hits = hits_section.get("hit", [])
        if not hits:
            break

        if isinstance(hits, dict):
            hits = [hits]

        for hit in hits:
            info = hit.get("info", {})
            title = str(info.get("title", "")).strip()
            venue = str(info.get("venue", "")).strip()
            url = str(info.get("url", "")).strip()
            authors = normalize_authors(info.get("authors"))
            papers.append(
                Paper(
                    conference=conference.upper(),
                    year=year,
                    title=title,
                    authors=authors,
                    venue=venue,
                    url=url,
                )
            )
            if len(papers) >= max_results:
                break

        offset += len(hits)
        if len(hits) < params["h"]:
            break

    return papers


def write_json(papers: list[Paper], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump([paper.as_dict() for paper in papers], f, ensure_ascii=False, indent=2)


def write_csv(papers: list[Paper], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["conference", "year", "title", "authors", "venue", "url"],
        )
        writer.writeheader()
        for paper in papers:
            row = paper.as_dict()
            row["authors"] = "; ".join(paper.authors)
            writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NeurIPS / ICML / ICLR / ACL の論文情報を DBLP API から取得します。"
    )
    parser.add_argument(
        "--conferences",
        nargs="+",
        default=["neurips", "icml", "iclr", "acl"],
        choices=sorted(CONFERENCE_STREAMS.keys()),
        help="取得対象カンファレンス (複数指定可)",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        required=True,
        help="取得対象の年 (例: --years 2023 2024)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=200,
        help="各 conference x year ごとの最大取得件数",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="DBLP API への 1 リクエストあたりの件数 (最大 1000)",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("outputs/papers.json"),
        help="JSON 出力先",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("outputs/papers.csv"),
        help="CSV 出力先",
    )

    args = parser.parse_args()
    if args.page_size <= 0 or args.page_size > 1000:
        parser.error("--page-size は 1〜1000 で指定してください。")
    if args.max_results <= 0:
        parser.error("--max-results は 1 以上で指定してください。")

    return args


def main() -> None:
    args = parse_args()
    all_papers: list[Paper] = []

    for conference in args.conferences:
        for year in args.years:
            papers = fetch_papers_for_conference(
                conference=conference,
                year=year,
                max_results=args.max_results,
                page_size=args.page_size,
            )
            print(f"{conference.upper()} {year}: {len(papers)} 件取得")
            all_papers.extend(papers)

    all_papers.sort(key=lambda p: (p.year, p.conference, p.title))
    write_json(all_papers, args.json_output)
    write_csv(all_papers, args.csv_output)
    print(f"JSON: {args.json_output}")
    print(f"CSV : {args.csv_output}")


if __name__ == "__main__":
    main()
