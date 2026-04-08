#### brew 
*   安装脚本 （自动选择软件源）
*   /bin/zsh -c "$(curl -fsSL https://gitee.com/cunkai/HomebrewCN/raw/master/Homebrew.sh)"
*   brew 卸载脚本
*   /bin/zsh -c "$(curl -fsSL https://gitee.com/cunkai/HomebrewCN/raw/master/HomebrewUninstall.sh)"

#### 常用命令
安装软件：brew install xxx
卸载软件：brew uninstall xxx
搜索软件：brew search xxx
更新软件：brew upgrade xxx
查看列表：brew list
更新brew：brew update
清理所有包的旧版本：brew cleanup
清理指定包的旧版本：brew cleanup $FORMULA
查看可清理的旧版本包，不执行实际操作：brew cleanup -n

#### Mongo 
sudo launchctl limit
sudo launchctl limit maxfiles 64000 64000
https://docs.mongodb.com/manual/reference/ulimit/
my remote mongo
name pass user:"my_mongodb",pwd:"my_mongodb"
https://www.jianshu.com/p/0a7452d8843d
'user':'dbadmin',pwd:'my_mongodb'
mac install mongo
mac install redis
brew install mangodb
brew install mongodb
brew tap mongodb/brew
brew install mongodb-community
launchctl limit maxfiles 2048 unlimited
brew services start mongodb-community
ps -ef |grep mongodb
mongo visual tool

##### Prob Solve
*   https://stackoverflow.com/questions/20931909/too-many-open-files-while-ensure-index-mongo
*   https://docs.mongodb.com/manual/reference/ulimit/
*   mac: sudo launchctl limit maxfiles 64000 64000

#### pip package
install pkuseg
https://github.com/explosion/spaCy/issues/6666
pip install https://github.com/lancopku/pkuseg-python/archive/master.zip

#### chrome driver
*   https://stackoverflow.com/questions/47148872/webdrivers-executable-may-have-wrong-permissions-please-see-https-sites-goo
*   mac: https://github.com/explosion/spaCy/issues/6666

#### stock info joint quant

#### Todo
*   1、新闻标签的分类，不能用股价，而是用分词，判断利好利空的属性。或者用分类器模型。
*   2、部分数据去空格，以免有重复数据。已经完成。
*   3、三套系统组合，人工智能。一是缠技术分析，二是新闻公告事件热点驱动，三是公司基本面。然后机械操作，降低成本。
*   4、分类器搞定，下面开始爬数据，解决数据重复爬取的问题。
*   5、两套文本打分系统，一种是根据切词结果直接统计 正面信息，负面信息，中性信息；二种是基于分类器来打分。

#### 港股数据爬取
*   https://www.akshare.xyz/zh_CN/latest/tutorial.html

#### matplot lib font problem solve
*   matplot 字体问题解决:~/.local/lib/python3.8/site-packages/matplotlib/mpl-data/fonts/ttf
*   https://blog.csdn.net/weixin_34184158/article/details/93173871
*   http://www.xiazaiziti.com/210356.html
*   matplotrc 删除注释行,https://matplotlib.org/3.2.1/gallery/text_labels_and_annotations/font_family_rc_sgskip.html
*   buy sell point