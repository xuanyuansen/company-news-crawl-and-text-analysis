#!/usr/bin/env python
# encoding: utf-8
import asyncio
from datetime import datetime, timedelta
from MarketNewsSpiderWithScrapy.BasePlayCrawler import Request, Response
from MarketNewsSpiderWithScrapy.BaseSpider import BaseSpider

class JQKASpider(BaseSpider):
    def __init__(
        self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 20
    ):
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)

    
    def start_requests(self):
        yield Request(self.start_url, callback=self.parse)
    
    async def parse(self, page, request):
        
        await page.goto(request.url, wait_until="networkidle")
        # 先下拉，再点击加载更多
        await self.scroll_test(page, times=2)
        await self.load_more_test(page)

        # 定位所有的头条新闻项 (包含 line-clamp-2 类名)
        news_items_selector = "a:has(.line-clamp-2)"
        try:
            await page.wait_for_selector(news_items_selector, timeout=3000)
            news_elements = await page.query_selector_all(news_items_selector)
        except Exception as e:
            print(f"[{self.name}] 未找到新闻列表: {e}")
            return

        for el in news_elements:
            # 提取 URL 和 标题
            url = await el.get_attribute("href")
            title_el = await el.query_selector(".line-clamp-2")
            title = (await title_el.inner_text()).strip() if title_el else ""

            if title and url:
                # 补全相对路径
                full_url = url if url.startswith("http") else f"https:{url}"
                
                # 构造 playInfos 结构
                # 根据要求：Article 为空，Date 为当前时间
                playInfos = {
                    "Title": title.split('\n')[0], # 清洗标题可能的换行
                    "Url": full_url,
                    "Article": "", # 按照要求设置为空
                    "Date": self.day_now, # 按照要求设置为 day_now
                    "Source": self.name
                }
                yield self.from_playInfos_to_item(playInfos)

    
    async def scroll_test(self, page, times=2):
        # 模拟加载更多 (滚动触发)
        for i in range(times):
            print(f"正在尝试下拉加载更多数据 (第 {i+1} 次)...")
            # 滚动到底部触发瀑布流加载
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            # 等待新内容渲染，同花顺接口响应通常需要 1-2 秒
            await asyncio.sleep(1) 

    async def load_more_test(self, page):
        # 模拟点击“加载更多” 
        for i in range(self.end_page):
            try:
                # 定位你提供的那个 span 元素
                load_more_btn = page.locator("span:has-text('加载更多')")
                if await load_more_btn.is_visible():
                    await load_more_btn.scroll_into_view_if_needed()
                    await load_more_btn.click()
                    print(f"第 {i+1} 次加载更多成功")
                    await page.wait_for_timeout(1000)
                else:
                    break
            except Exception as e:
                break
