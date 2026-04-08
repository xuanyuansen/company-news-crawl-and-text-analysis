from datetime import datetime, timedelta
from MarketNewsSpiderWithScrapy.BasePlayCrawler import Request, Response
from MarketNewsSpiderWithScrapy.BaseSpider import BaseSpider
import re


class JRJSpider(BaseSpider):
    name = "jrj_news"

    def __init__(self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 1):
        # 初始化父类，加载 NLP 模型和数据库配置
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)

    def start_requests(self):
        yield Request(self.start_url, callback=self.parse)

    async def parse(self, response):
        page = response.page
        print(f"[{self.name}] 正在解析列表页: {response.url}")

        # 1. 处理“加载更多”逻辑（根据 end_page 决定点击次数）
        for i in range(self.end_page):
            load_more_btn = await page.query_selector("#awwmore")
            if load_more_btn and await load_more_btn.is_visible():
                print(f"[{self.name}] 点击加载更多 (第 {i+1} 次)...")
                await load_more_btn.click()
                await page.wait_for_timeout(2000)

        # 2. 定位所有新闻项
        key_words = "#newsList .news_item"
        await page.wait_for_selector(key_words, timeout=10000)
        news_elements = await page.query_selector_all(key_words)

        for el in news_elements:
            url = await el.get_attribute("href")
            title_el = await el.query_selector("b") 
            title = (await title_el.inner_text()).strip() if title_el else (await el.inner_text()).strip()
            
            # 清洗标题
            clean_title = title.split('\n')[0] 

            # 构造元数据传递给详情页
            meta_data = {
                "title": clean_title,
                "url": url
            }
            
            # 这里的 Request 会被 PlaywrightCrawlerProcess 捕获并进入下一次循环
            yield Request(url, callback=self.parse_detail, meta=meta_data)

    async def parse_detail(self, response):
        page = response.page
        meta = response.meta
        detail_url = response.url

        try:
            # 1. 提取发布时间
            time_selector = ".article_info span, .titmain"
            time_el = await page.query_selector(time_selector)
            raw_time = ""
            if time_el:
                text = (await time_el.inner_text()).strip()
                # 正则匹配标准日期格式
                time_match = re.search(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(:\d{2})?', text)
                raw_time = time_match.group() if time_match else self.day_now

            # 头条时间获取与其他网页不同
            if not raw_time:
                raw_time = await page.evaluate("() => window.makedate || ''")
            # print(raw_time)
            # 2. 提取正文内容
            content_selector = ".article_content, .text-main, .Article, #mainText"
            await page.wait_for_selector(content_selector, timeout=5000)
            content_el = await page.query_selector(content_selector)
            article_text = ""
            if content_el:
                # 提取正文文本，并进行简单的清洗
                article_text = (await content_el.inner_text()).strip()
            
            # 构造 playInfos 字典
            playInfos = {
                "Title": meta.get('title', '无标题'),
                "Date": raw_time,
                "Url": detail_url,
                "Article": article_text,
                "Source": self.name
            }

            item = self.from_playInfos_to_item(playInfos)
            
            yield item

        except Exception as e:
            print(f"[{self.name}] 详情页解析失败 {detail_url}: {e}")