#### Todo
*   1、新闻标签的分类，不能用股价，而是用分词，判断利好利空的属性。或者用分类器模型。
*   2、部分数据去空格，以免有重复数据。已经完成。
*   3、三套系统组合，人工智能。一是缠技术分析，二是新闻公告事件热点驱动，三是公司基本面。然后机械操作，降低成本。
*   4、分类器搞定，下面开始爬数据，解决数据重复爬取的问题。
*   5、两套文本打分系统，一种是根据切词结果直接统计 正面信息，负面信息，中性信息；二种是基于分类器来打分。

#### Prob Solve
*   https://stackoverflow.com/questions/20931909/too-many-open-files-while-ensure-index-mongo
*   sudo launchctl limit maxfiles 1024 2048