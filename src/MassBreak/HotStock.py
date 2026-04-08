from Utils.utils import set_display
from tqdm import tqdm
import akshare as ak


tqdm.pandas(desc="progress status")

set_display()

if __name__ == "__main__":
    # 千股千评
    "stock_comment_em"  # 股市关注度
    "stock_comment_detail_zlkp_jgcyd_em"  # 机构参与度
    "stock_comment_detail_zhpj_lspf_em"  # 综合评价-历史评分
    "stock_comment_detail_scrd_focus_em"  # 市场热度-用户关注指数
    "stock_comment_detail_scrd_desire_em"  # 市场热度-市场参与意愿
    "stock_comment_detail_scrd_desire_daily_em"  # 市场热度-日度市场参与意愿
    "stock_comment_detail_scrd_cost_em"  # 市场热度-市场成本

    print(ak.stock_fund_flow_concept())
    pass