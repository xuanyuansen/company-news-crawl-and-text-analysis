# python get_stock_price_info.py -m cn -s 2025-12-01
# python get_stock_price_info.py -m us -s 2026-01-01  # 已经获取了0101-0315的数据

cd /home/zhangSongbo/work/work/company-news-crawl-and-text-analysis/src/
# echo "cd"
/home/zhangSongbo/miniconda3/envs/py312env/bin/python run_scrapy_one_day.py -s 1 -r 1 > ./logs/info.log 2> ./logs/error.log
/home/zhangSongbo/miniconda3/envs/py312env/bin/python get_stock_price_info.py -m cn -s 2026-03-12 > ./logs/get_cn_stock_price_info.log
# /home/zhangSongbo/miniconda3/envs/py312env/bin/python get_stock_price_info.py -m us -s 2026-03-10 > ./logs/get_us_stock_price_info.log

# GetMassBreakAlphaGo.py
# python GetMassBreakAlphaGo.py <股票代码> <市场类型> <开始日期> <平均天数> <放量倍数>
# python GetMassBreakAlphaGo.py sh603291 cn 2026-01-01 30 1.2


# cd /home/zhangSongbo/work/work/company-news-crawl-and-text-analysis/src
# python MassBreak/MassBreakAndInfosAlphaGo.py \
#   --market cn --start-date 2026-02-01 --ave-date 10 --ratio 1.5 --keep-days 3 \
#   --price-stable-threshold 0.05 --min-break-count 1 --news-start-date 2026-03-01 


# python VnpyBacktesting/back_test.py --market cn --symbols sh603938 --start-date 2026-02-01 --end-date 2026-03-16 --buy-date 2026-03-04

# python VnpyBacktesting/back_test.py \
#   --symbols sh603938,sh603139 \
#   --start-date 2026-02-01 \
#   --end-date 2026-03-16 \
#   --symbol-buy-dates sh603938:2026-03-04,sh603139:2026-03-06 \
#   --no-show-chart --no-save-chart


# python Utils/stock_news_wordcloud.py --start-date 2026-03-01 --end-date 2026-03-16 --output ./Utils/stock_name_wordcloud_2026-03-01_2026-03-16.png --freq-csv ./Utils/stock_name_wordcloud_2026-03-01_2026-03-16.csv 
# transformers    vnpy    vnpy_ctastrategy       vnpy_sqlite   

# topn进行批量回测
# cd /home/zhangSongbo/work/work/vnpy/company-news-crawl-and-text-analysis/src
# python VnpyBacktesting/back_test_topn.py \
#   --top-n 20 \
#   --market cn \
#   --start-date 2026-02-01 \
#   --end-date 2026-03-16 \
#   --ave-date 10 \
#   --ratio 1.5 \
#   --keep-days 3 \
#   --price-stable-threshold 0.05 \
#   --min-break-count 1 \
#   --news-start-date 2026-03-01 \
#   --as-of-date 2026-03-16 \
#   --no-show-chart --no-save-chart
