from datetime import datetime, timedelta
from MarketNewsSpiderWithScrapy.BasePlayCrawler import Request, Response
from MarketNewsSpiderWithScrapy.BaseSpider import BaseSpider

class EastMoneySpider(BaseSpider):
    name = "east_money"
    def __init__(
        self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 2,
    ):
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)

    def start_requests(self):
        # 生成 URL 列表
        urls = [self.start_url] + [
            self.start_url.replace(".html", "_{0}.html".format(xid))
            for xid in range(2, self.end_page + 1)
        ]
        for url in urls:
            yield Request(url, callback=self.parse)

    async def parse(self, response):
        page = response.page
        print(f"正在解析列表页: {response.url}")
        
        # 1. 等待列表加载
        try:
            await page.wait_for_selector("#newsListContent li", timeout=10000)
        except Exception as e:
            print(f"列表页加载超时: {e}")
            return

        # 2. 提取数据
        li_elements = await page.query_selector_all("#newsListContent li")
        
        for li in li_elements:
            title_el = await li.query_selector(".title a")
            time_el = await li.query_selector(".time")
            
            if title_el and time_el:
                url = await title_el.get_attribute("href")
                title = (await title_el.inner_text()).strip()
                time_str = (await time_el.inner_text()).strip()
                
                # 简单的日期处理（可根据需要复用你之前的完整逻辑）
                meta_data = {
                    'title': title, 
                    'date': time_str
                }
                
                # Yield 请求：跳转到详情页
                yield Request(url, callback=self.parse_detail, meta=meta_data)

    async def parse_detail(self, response):
        page = response.page
        meta = response.meta
        
        # 1. 提取正文
        content = ""
        try:
            # 兼容普通新闻和财富号
            await page.wait_for_selector(".Body, #ContentBody, .article-body", timeout=5000)
            content_el = await page.query_selector(".Body, #ContentBody, .article-body")
            if content_el:
                content = await content_el.inner_text()
        except:
            print(f"正文提取失败: {response.url}")
        
        # 2. Yield Item (注意：这里使用大写 Key 以匹配 Engine 的 print)
        playInfos =  {
            "Title": meta.get('title', '无标题'),    # 对应 Engine 中的 res.get('Title')
            "Date": meta.get('date', ''),
            "Url": response.url,
            "Article": content.strip(),
            "Source": self.name
        }
        yield self.from_playInfos_to_item(playInfos)

