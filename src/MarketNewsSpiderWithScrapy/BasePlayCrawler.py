from scrapy.http import Request
import asyncio, random
from playwright.async_api import async_playwright
from pipelines import MongoDBPipeline

class Request:
    """模拟 Scrapy Request"""
    def __init__(self, url, callback, meta=None, dont_filter=False):
        self.url = url
        self.callback = callback
        self.meta = meta or {}
        self.dont_filter = dont_filter

class Response:
    """模拟 Scrapy Response"""
    def __init__(self, url, page, meta):
        self.url = url
        self.page = page
        self.meta = meta

class PlaywrightCrawlerProcess:
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.spiders = []  # 存储待运行的爬虫实例
        self.pipeline = MongoDBPipeline()

    def crawl(self, spider_cls, **kwargs):
        """
        接收爬虫类和参数，实例化爬虫并加入队列
        """
        spider = spider_cls(**kwargs)
        self.spiders.append(spider)

    def start(self):
        """
        阻塞式启动，就像 Scrapy 的 process.start()
        """
        print(f"CrawlerProcess 启动，共 {len(self.spiders)} 个爬虫任务...")
        asyncio.run(self._run_async())

    async def _run_async(self):
        """
        异步主循环：启动浏览器 -> 并发运行所有爬虫 -> 关闭浏览器
        """
        async with async_playwright() as p:
            # 根据 settings 配置浏览器
            headless = self.settings.get('headless', True)
            browser = await p.chromium.launch(headless=headless)
            
            # 为每个爬虫创建一个独立的运行任务
            tasks = []
            for spider in self.spiders:
                # 这一点很关键：所有爬虫共享 Browser，但拥有独立的 Context
                # 这样 cookie 互不干扰，且节省内存
                task = self._run_single_spider(spider, browser)
                tasks.append(task)
            
            # 并发执行所有爬虫
            await asyncio.gather(*tasks)
            
            await browser.close()
            print("所有爬虫任务完成，浏览器已关闭。")

    async def _run_single_spider(self, spider, browser):
        """
        单个爬虫的调度逻辑
        """
        print(f"[{spider.name}] 开始运行...")
        
        # 创建独立的上下文
        user_agent = random.choice(self.settings.get('USER_AGENTS', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"))
        context = await browser.new_context(
            user_agent=user_agent
        )
        page = await context.new_page()
        
        # 获取初始请求
        if hasattr(spider, 'start_requests'):
            request_queue = list(spider.start_requests())
        else:
            request_queue = []

        item_count = 0
        
        try:
            while request_queue:
                req = request_queue.pop(0)
                try:
                    if "shanghai" in spider.name or 'jqka' in spider.name: 
                        callback_result = req.callback(page, req)
                    else:
                        # 执行页面跳转
                        # 可以在这里根据 settings 增加全局超时控制
                        await page.goto(req.url, wait_until="domcontentloaded", timeout=50000)
                        response = Response(req.url, page, req.meta)
                        
                        # 执行回调
                        callback_result = req.callback(response)
                    
                    # 处理回调生成器
                    if hasattr(callback_result, '__aiter__'):
                        async for res in callback_result:
                            if isinstance(res, Request):
                                request_queue.insert(0, res) 
                            elif isinstance(res, dict) or hasattr(res, 'keys'):
                                item_count += 1
                                # 这里可以加 Pipeline 处理逻辑，比如存库
                                self.pipeline.process_item(res, spider)
                                if hasattr(spider, 'process_item'):
                                    spider.process_item(res)
                                else:
                                    print(f"[{spider.name}] Item: {res.get('Title', 'No Title')}")
                except Exception as e:
                    print(f"[{spider.name}] 请求错误 {req.url}: {e}")
                    
        finally:
            await context.close()
            print(f"[{spider.name}] 运行结束，共抓取 {item_count} 条数据。")

