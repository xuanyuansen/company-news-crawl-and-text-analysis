import asyncio
from datetime import datetime, timedelta
from MarketNewsSpiderWithScrapy.BasePlayCrawler import Request, Response
from MarketNewsSpiderWithScrapy.BaseSpider import BaseSpider

class ShanghaiStockSpider(BaseSpider):

    def __init__(self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 2):
        # 初始化父类（加载 NLP 模型和数据库连接）
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)
        self.captured_items = []

    def start_requests(self):
        yield Request(self.start_url, callback=self.parse)

    async def parse(self, page, request):
        # 1. 注册 AJAX 拦截器
        async def handle_response(response):
            try:
                if response.status == 200 and "application/json" in response.headers.get("content-type", ""):
                    res_json = await response.json()
                    data_node = res_json.get("data", {})
                    items = data_node.get("list") or data_node.get("pageInfo", {}).get("list", [])
                    if items:
                        self.captured_items.extend(items)
            except: pass

        page.on("response", handle_response)
        await page.goto(request.url, wait_until="networkidle")

        # 2. 模拟加载更多
        for i in range(self.end_page):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.evaluate("window.scrollBy(0, -50)") # 稍微回滚触发
            await asyncio.sleep(1) # 等待数据拦截

        # 3. 产出标准 Item
        for raw in self.captured_items:
            share_info = raw.get("shareInfo", {})
            date_info = share_info.get("dateInfo", {})
            if date_info:
                year = date_info.get("year", datetime.now().year)
                month = date_info.get("month", "01")
                day = date_info.get("day", "01")
                hour = date_info.get("hour", "00")
                minute = date_info.get("minute", "00")
                pub_time = f"{year}-{month}-{day} {hour}:{minute}"
            else:
                pub_time = self.day_now

            # 这里的 Article 直接使用摘要
            playInfos = {
                "Title": share_info.get("title") or raw.get("name", ""),
                "Url": share_info.get("shareUrl", ""),
                "Article": share_info.get("summary", ""),
                "Date": pub_time,
                "Source": self.name
            }
            yield self.from_playInfos_to_item(playInfos)
