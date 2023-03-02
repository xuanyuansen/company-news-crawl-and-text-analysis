#### 整体架构说明
代码主要包括几大部分功能
*   股票新闻爬取，并通过模型来判断新闻是正面消息还是负面消息
*   股票价格爬取，目前通过akshare来实现，joint quant框架已经不再使用
*   股票价格分析，包括基于基本面数据的分析，以及基于缠论的技术分析

#### 代码的组织
* ChanTechAnalyze，缠论技术分析
* FundamentalMarketAnalyze，基本面分析
* [run_scripy_spider.py](src%2Frun_scripy_spider.py) 基于配置，爬取全部新闻
* [run_scrapy_one_day.py](src%2Frun_scrapy_one_day.py) 基于配置，爬取当日新闻

#### 原始代码设计不好，所以全部重新基于scrapy来实现。

#### 中文常用停用词表

| 词表名 | 词表文件 |
| ---- | ---- |
| 中文停用词表                   | cn\_stopwords.txt    |
| 哈工大停用词表                 | hit\_stopwords.txt   |
| 百度停用词表                   | baidu\_stopwords.txt |
| 四川大学机器智能实验室停用词库 | scu\_stopwords.txt   |

#### To do
*   挖掘牛股模式，还要继续加油！！！
*   重点找方差小的，成交量突然起伏的！！
*   日线为主，周线为辅助，例如sz300339的模式。