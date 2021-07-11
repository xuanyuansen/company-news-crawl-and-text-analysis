import pandas as pd
import requests
import json
import numpy as np
from pyspark.sql.types import *
import torch.nn.functional as F

loss = F.cross_entropy()


# "_id", "Domain", "Tag", "Title", "Text", "Urls", "Cnt", "Label"
mySchema = StructType([ StructField("id", StringType(), True) \
                       ,StructField("Domain", StringType(), True)\
                       ,StructField("Tag", StringType(), True)\
                       ,StructField("Title", StringType(), True)\
                       ,StructField("Text", StringType(), True)\
                       ,StructField("Urls", StringType(), True)\
                       ,StructField("Cnt", IntegerType(), True)\
                       ,StructField("Label", StringType(), True)\
                       ,StructField("Score", FloatType(), True)])
a = pd.DataFrame()

for _idx, row in a.iterrows():
    print(_idx)
header = {'Content-type':'application/json'}

row_data = [{"domain": "www.fanshengyun.com", "title": "《大巧休夫》下集_华云视听——云南本土原创视频网",
             "text": "首页所有分类所有视频最新视频最热视频MV视频云南山歌山歌剧 对 唱类 预告片网剧短片花灯剧免费视频山歌"
                     "剧山歌对唱VIP代理上传移动端QQ登录微信登录登录注册注册登录南柯一梦花灯剧发表评论济公收痨虫25042大巧休夫下集"
                     "26201杀狗劝妻36513大 巧休夫上 集40992众视界ICP备案号滇ICP备17002271号"
                     "1Copyrightc20182020AllRightsReserved"}, {"url": "https://www.jb51.net/article/99453.htm"},
            {"url":"http://china.cnr.cn/gdgg/20210705/t20210705_525527525.shtml"}]

_query = json.dumps(row_data, ensure_ascii=False)
print(_query)
res = requests.post(url="http://scc-ml-pipeline.byted.org/predictions/scc_text_classify_torch",
                    headers=header, data=_query.encode('utf-8'))

_in = json.loads(res.content.decode("utf-8"))
print(type(_in))
_in = [json.loads(ele) for ele in _in]
print(_in)
out_data = pd.json_normalize(_in)
print(out_data)

res2 = pd.DataFrame(np.zeros((3, 2)), index=[1, 2, 3],columns=['_label', '_score'])
res2 = res2.reset_index(drop=True)
print(res2)

_res = pd.concat([out_data, res2], axis=1)
print(_res)
_res['test'] = _res.apply(lambda row: str(row['prob']), axis=1)
_res = _res[(_res['test'].str.len()>1 )&( _res['test'].str.len()>2)]
print(_res)

a = _res.dropna(axis=0, how='any')
print('drop {}'.format(a))