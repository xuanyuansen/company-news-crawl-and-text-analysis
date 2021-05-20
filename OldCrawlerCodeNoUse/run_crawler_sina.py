from crawler_sina import WebCrawlFromSina

if __name__ == "__main__":
    web_crawl_obj = WebCrawlFromSina(
        20,
        1,
        ThreadsNum=4,
        IP="localhost",
        PORT=27017,
        dbName="Sina_Stock",
        collectionName="sina_news_company",
    )
    web_crawl_obj.coroutine_run()  # web_crawl_obj.single_run() #web_crawl_obj.multi_threads_run()
