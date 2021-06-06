#### Todo
*   1、新闻标签的分类，不能用股价，而是用分词，判断利好利空的属性。或者用分类器模型。
*   2、部分数据去空格，以免有重复数据。已经完成。
*   3、三套系统组合，人工智能。一是缠技术分析，二是新闻公告事件热点驱动，三是公司基本面。然后机械操作，降低成本。
*   4、分类器搞定，下面开始爬数据，解决数据重复爬取的问题。
*   5、两套文本打分系统，一种是根据切词结果直接统计 正面信息，负面信息，中性信息；二种是基于分类器来打分。

#### Prob Solve
*   https://stackoverflow.com/questions/20931909/too-many-open-files-while-ensure-index-mongo
*   https://docs.mongodb.com/manual/reference/ulimit/
*   mac: sudo launchctl limit maxfiles 64000 64000

#### 港股数据爬取
*   https://www.akshare.xyz/zh_CN/latest/tutorial.html

#### matplot lib font problem solve
*   matplot 字体问题解决:~/.local/lib/python3.8/site-packages/matplotlib/mpl-data/fonts/ttf
*   https://blog.csdn.net/weixin_34184158/article/details/93173871
*   http://www.xiazaiziti.com/210356.html
*   matplotrc 删除注释行,https://matplotlib.org/3.2.1/gallery/text_labels_and_annotations/font_family_rc_sgskip.html
*   buy sell point