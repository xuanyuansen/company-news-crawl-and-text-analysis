# -*- coding:utf-8 -*-
import asyncio
import random
import re
from typing import Optional

from bs4 import BeautifulSoup

from MarketNewsSpiderWithScrapy.BasePlayCrawler import Request
from MarketNewsSpiderWithScrapy.BaseSpider import BaseSpider


REQUEST_DELAY = (2.0, 5.0)
RETRY_TIMES = 2
TIMEOUT_MS = 50_000
DETAIL_TIMEOUT_MS = 15_000

BLOCK_KEYWORDS = (
    "Just a moment",
    "Checking your browser",
    "请稍候",
    "人机验证",
    "执行安全验证",
)


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def build_list_url(base_url: str, page: int) -> str:
    return re.sub(r"-\d+\.shtml$", f"-{page}.shtml", base_url)


def _is_blocked_page(title: str, content: str) -> bool:
    return any(keyword in title or keyword in content for keyword in BLOCK_KEYWORDS)


async def human_behavior(page) -> None:
    await asyncio.sleep(random.uniform(*REQUEST_DELAY))

    for _ in range(random.randint(2, 4)):
        scroll_y = random.randint(300, 800)
        await page.evaluate(f"window.scrollBy({{ top: {scroll_y}, behavior: 'smooth' }})")
        await asyncio.sleep(random.uniform(0.5, 1.5))

    for _ in range(random.randint(2, 4)):
        x = random.randint(200, 1700)
        y = random.randint(200, 800)
        await page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.1, 0.4))

    await page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
    await asyncio.sleep(0.5)


def parse_list_items(html: str, list_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items: list[dict] = []

    for card in soup.select("div.card-text-wrap"):
        title_link = card.select_one("h3.h3-large a[href*='/story/']")
        if not title_link:
            continue

        info_el = card.select_one("div.card-text-info")
        info_text = _clean_text(info_el.get_text("|", strip=True) if info_el else "")
        date_text = ""
        source_text = ""
        if info_text:
            parts = [part.strip() for part in info_text.split("|") if part.strip()]
            date_text = parts[0] if parts else ""
            source_text = parts[1] if len(parts) > 1 else ""

        summary_el = card.select_one("p.card-text-summary")
        category_el = card.select_one("div.card-text-type")
        url = title_link.get("href", "")
        if url and not url.startswith("http"):
            url = BASE_URL + url

        items.append(
            {
                "title": _clean_text(title_link.get_text(" ", strip=True)),
                "url": url,
                "date": date_text,
                "source": source_text,
                "summary": _clean_text(summary_el.get_text(" ", strip=True) if summary_el else ""),
                "theme_tags": _clean_text(category_el.get_text(" ", strip=True) if category_el else ""),
                "list_url": list_url,
            }
        )

    if items:
        return items

    for link in soup.select("a[href*='/story/']"):
        title = _clean_text(link.get_text(" ", strip=True))
        if not title:
            continue
        href = link.get("href", "")
        if href and not href.startswith("http"):
            href = BASE_URL + href
        items.append(
            {
                "title": title,
                "url": href,
                "date": "",
                "source": "",
                "summary": "",
                "theme_tags": "",
                "list_url": list_url,
            }
        )

    return items


def parse_detail_item(html: str, url: str, source_title: str, date_hint: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    headline = (
        soup.select_one("h1.headline#contenttitle")
        or soup.select_one("h1.headline")
        or soup.find("h1")
    )
    title = _clean_text(headline.get_text(" ", strip=True) if headline else source_title)

    company = ""
    date_text = date_hint
    company_block = soup.select_one("div.storyview-company")
    if company_block:
        company_link = company_block.find("a")
        if company_link is not None:
            company = _clean_text(company_link.get_text(" ", strip=True))
        company_text = " ".join(company_block.stripped_strings)
        match = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", company_text)
        if match:
            date_text = match.group(0)

    article = ""
    text_block = soup.select_one("div.text-block")
    if text_block:
        content_nodes = [
            node
            for node in text_block.find_all(recursive=False)
            if node.name == "div" and not node.get("class") and node.get("id") != "storyList"
        ]
        if content_nodes:
            content_root = max(content_nodes, key=lambda node: len(_clean_text(node.get_text(" ", strip=True))))
            paragraphs = [
                _clean_text(tag.get_text(" ", strip=True))
                for tag in content_root.find_all(["p", "li"])
                if _clean_text(tag.get_text(" ", strip=True))
            ]
            article = "\n".join(paragraphs) if paragraphs else _clean_text(content_root.get_text(" ", strip=True))

    return {
        "title": title,
        "url": url,
        "date": date_text,
        "source": company,
        "article": article,
    }


class MeiTongSpider(BaseSpider):
    name = "mei_tong"

    def __init__(
        self,
        name,
        key_word,
        key_word_chn,
        start_url,
        base_url,
        end_page: int = 2,
        ):
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)

    def _start_urls(self) -> list[str]:
        start_url = getattr(self, "start_url", "")
        if start_url:
            return [start_url]

    def start_requests(self):
        page_limit = max(1, int(getattr(self, "end_page", 1)))
        for base_url in self._start_urls():
            for page_num in range(1, page_limit + 1):
                list_url = build_list_url(base_url, page_num)
                yield Request(
                    list_url,
                    callback=self.parse,
                    meta={
                        "base_url": base_url,
                        "page_num": page_num,
                        "list_url": list_url,
                    },
                )

    async def parse(self, response):
        page = response.page
        list_url = response.meta.get("list_url", response.url)
        self.logger.info("[%s] 正在解析列表页: %s", self.name, response.url)

        try:
            await page.wait_for_selector("div.card-text-wrap, a[href*='/story/']", timeout=TIMEOUT_MS)
            title = await page.title()
            content = await page.content()
            if _is_blocked_page(title, content):
                self.logger.warning("[%s] 列表页被验证页拦截: %s", self.name, response.url)
                return

            await human_behavior(page)
            html = await page.content()
            list_items = parse_list_items(html, list_url)
            if not list_items:
                self.logger.warning("[%s] 列表页没有解析到数据: %s", self.name, response.url)
                return

            for item in list_items:
                meta_data = {
                    "title": item.get("title", "无标题"),
                    "date": item.get("date", ""),
                    "source": item.get("source", ""),
                    "summary": item.get("summary", ""),
                    "theme_tags": item.get("theme_tags", ""),
                    "list_url": item.get("list_url", list_url),
                }
                yield Request(item["url"], callback=self.parse_detail, meta=meta_data, dont_filter=True)
        except Exception as exc:
            self.logger.warning("[%s] 列表页解析失败 %s: %s", self.name, response.url, exc)

    async def parse_detail(self, response):
        page = response.page
        meta = response.meta
        detail_url = response.url
        self.logger.info("[%s] 正在解析详情页: %s", self.name, detail_url)

        try:
            await page.wait_for_selector("h1.headline, div.text-block, div.storyview-company", timeout=DETAIL_TIMEOUT_MS)
            title = await page.title()
            content = await page.content()
            if _is_blocked_page(title, content):
                self.logger.warning("[%s] 详情页被验证页拦截: %s", self.name, detail_url)
                return

            await human_behavior(page)
            html = await page.content()
            detail = parse_detail_item(
                html,
                detail_url,
                meta.get("title", "无标题"),
                meta.get("date", ""),
            )
            play_infos = {
                "Title": detail["title"],
                "Date": detail["date"],
                "Url": detail["url"],
                "Article": detail["article"],
                "Source": self.name,
            }
            # print(play_infos)
            yield self.from_playInfos_to_item(play_infos)
        except Exception as exc:
            self.logger.warning("[%s] 详情页解析失败 %s: %s", self.name, detail_url, exc)
