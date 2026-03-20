from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict

from PIL import Image, ImageDraw, ImageFont

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from Utils import config
from Utils.database import Database

DEFAULT_EXCLUDE_NAMES = {"东方财富", "机器人"}
SECURITY_INSTITUTION_NAMES = {
    "中信证券",
    "中信建投",
    "国泰海通",
    "海通证券",
    "海通",
    "华泰证券",
    "东吴证券",
    "国金证券",
    "广发证券",
    "招商证券",
    "国信证券",
    "银河证券",
    "申万宏源",
    "方正证券",
    "光大证券",
    "长江证券",
    "中金公司",
}


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def to_cn_date_start(value: datetime) -> str:
    return value.strftime("%Y年%m月%d日 00:00")


def to_cn_date_end(value: datetime) -> str:
    return value.strftime("%Y年%m月%d日 23:59")


def resolve_font_path(user_font_path: str = "") -> str:
    if user_font_path:
        p = Path(user_font_path)
        if not p.exists():
            raise FileNotFoundError(f"font not found: {p}")
        return str(p)

    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    raise FileNotFoundError("no usable font found, please pass --font-path")


def clean_stock_name(name: str, fallback: str) -> str:
    if not name:
        return fallback
    name = str(name).strip()
    return name if name else fallback


def build_name_frequency(
    start_date: datetime,
    end_date: datetime,
    db_name: str,
    min_mentions: int,
    max_collections: int,
) -> Dict[str, int]:
    start_cn = to_cn_date_start(start_date)
    end_cn = to_cn_date_end(end_date)

    db = Database()
    news_db = db.connect_database(db_name)
    collection_names = sorted(news_db.list_collection_names())
    if max_collections > 0:
        collection_names = collection_names[:max_collections]

    query = {"Date": {"$gte": start_cn, "$lte": end_cn}}
    freq: Counter[str] = Counter()

    for col_name in collection_names:
        col = news_db.get_collection(col_name)
        cnt = int(col.count_documents(query))
        if cnt < min_mentions:
            continue

        doc = col.find_one(query, {"Name": 1}, sort=[("Date", -1)])
        stock_name = clean_stock_name(doc.get("Name", "") if doc else "", col_name)
        freq[stock_name] += cnt

    return dict(freq)


def is_security_institution_name(name: str) -> bool:
    text = str(name).strip()
    if not text:
        return False
    if text in SECURITY_INSTITUTION_NAMES:
        return True
    return "证券" in text


def filter_name_frequency(
    frequencies: Dict[str, int],
    exclude_names: set[str],
    exclude_securities: bool,
) -> tuple[Dict[str, int], Dict[str, int]]:
    keep: Dict[str, int] = {}
    dropped: Dict[str, int] = {}
    for name, cnt in frequencies.items():
        if name in exclude_names:
            dropped[name] = cnt
            continue
        if exclude_securities and is_security_institution_name(name):
            dropped[name] = cnt
            continue
        keep[name] = cnt
    return keep, dropped


def generate_wordcloud_with_wordcloud_lib(
    frequencies: Dict[str, int],
    output_path: Path,
    font_path: str,
    width: int,
    height: int,
    max_words: int,
    background_color: str,
) -> bool:
    try:
        from wordcloud import WordCloud
    except Exception:
        return False

    wc = WordCloud(
        font_path=font_path,
        width=width,
        height=height,
        background_color=background_color,
        max_words=max_words,
        collocations=False,
    )
    wc.generate_from_frequencies(frequencies)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wc.to_file(str(output_path))
    return True


def overlap(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> bool:
    return not (
        box_a[2] < box_b[0]
        or box_b[2] < box_a[0]
        or box_a[3] < box_b[1]
        or box_b[3] < box_a[1]
    )


def generate_wordcloud_with_pil(
    frequencies: Dict[str, int],
    output_path: Path,
    font_path: str,
    width: int,
    height: int,
    max_words: int,
    background_color: str,
    seed: int = 42,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(img)
    rnd = random.Random(seed)

    items = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)[:max_words]
    if not items:
        raise ValueError("no stock names found in date range")

    counts = [c for _, c in items]
    c_max = max(counts)
    c_min = min(counts)
    font_max = max(36, min(130, int(height * 0.15)))
    font_min = max(14, min(28, int(height * 0.02)))

    def size_for_count(cnt: int) -> int:
        if c_max == c_min:
            return (font_max + font_min) // 2
        ratio = (cnt - c_min) / float(c_max - c_min)
        return int(font_min + ratio * (font_max - font_min))

    colors = [
        (36, 87, 158),
        (32, 143, 120),
        (192, 95, 47),
        (156, 67, 105),
        (89, 98, 185),
        (65, 121, 63),
    ]

    boxes: list[tuple[int, int, int, int]] = []
    margin = 4

    for idx, (word, cnt) in enumerate(items):
        font_size = size_for_count(cnt)
        placed = False

        for _ in range(200):
            font = ImageFont.truetype(font_path, font_size)
            left, top, right, bottom = draw.textbbox((0, 0), word, font=font)
            w = right - left
            h = bottom - top

            if w >= width - 2 or h >= height - 2:
                font_size = max(font_min, font_size - 2)
                continue

            x = rnd.randint(0, max(0, width - w - 1))
            y = rnd.randint(0, max(0, height - h - 1))
            box = (x - margin, y - margin, x + w + margin, y + h + margin)

            if any(overlap(box, b) for b in boxes):
                continue

            draw.text((x, y), word, font=font, fill=colors[idx % len(colors)])
            boxes.append(box)
            placed = True
            break

        if not placed:
            continue

    img.save(output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate stock-name word cloud from MongoDB stock_specific_news."
    )
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--db-name",
        default=config.ALL_NEWS_OF_SPECIFIC_STOCK_DATABASE,
        help="MongoDB database name, default: stock_specific_news",
    )
    parser.add_argument("--font-path", default="", help="Chinese font file path")
    parser.add_argument("--output", default="", help="output png path")
    parser.add_argument("--freq-csv", default="", help="output frequency csv path")
    parser.add_argument("--width", type=int, default=1800)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--max-words", type=int, default=200)
    parser.add_argument("--min-mentions", type=int, default=1, help="min news count per stock")
    parser.add_argument(
        "--max-collections",
        type=int,
        default=0,
        help="debug only, limit number of stock collections to scan",
    )
    parser.add_argument("--background-color", default="white")
    parser.add_argument(
        "--exclude-names",
        default="东方财富,机器人",
        help="comma-separated stock names to exclude",
    )
    parser.add_argument(
        "--include-securities",
        action="store_true",
        help="include securities institutions in result (default: excluded)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)
    if start_date > end_date:
        raise ValueError("start-date must be <= end-date")

    out_png = (
        Path(args.output)
        if args.output
        else Path(__file__).resolve().parent / f"stock_name_wordcloud_{args.start_date}_{args.end_date}.png"
    )
    out_csv = (
        Path(args.freq_csv)
        if args.freq_csv
        else out_png.with_suffix(".csv")
    )
    font_path = resolve_font_path(args.font_path)

    freq = build_name_frequency(
        start_date=start_date,
        end_date=end_date,
        db_name=args.db_name,
        min_mentions=max(1, int(args.min_mentions)),
        max_collections=max(0, int(args.max_collections)),
    )
    exclude_names = {
        n.strip()
        for n in (args.exclude_names.split(",") if args.exclude_names else [])
        if n.strip()
    }
    exclude_names.update(DEFAULT_EXCLUDE_NAMES)
    freq, dropped = filter_name_frequency(
        frequencies=freq,
        exclude_names=exclude_names,
        exclude_securities=not args.include_securities,
    )
    if not freq:
        raise ValueError("no stock news found after applying exclusion filters")

    import pandas as pd

    freq_df = (
        pd.DataFrame(
            [{"stock_name": name, "news_count": cnt} for name, cnt in freq.items()]
        )
        .sort_values(by="news_count", ascending=False)
        .reset_index(drop=True)
    )
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    freq_df.to_csv(out_csv, index=False)

    generated = generate_wordcloud_with_wordcloud_lib(
        frequencies=freq,
        output_path=out_png,
        font_path=font_path,
        width=args.width,
        height=args.height,
        max_words=args.max_words,
        background_color=args.background_color,
    )
    if not generated:
        generate_wordcloud_with_pil(
            frequencies=freq,
            output_path=out_png,
            font_path=font_path,
            width=args.width,
            height=args.height,
            max_words=args.max_words,
            background_color=args.background_color,
        )

    print(f"word cloud saved: {out_png}")
    print(f"frequency csv saved: {out_csv}")
    print(f"excluded names count: {len(dropped)}")
    print("top 20 stock names:")
    print(freq_df.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
