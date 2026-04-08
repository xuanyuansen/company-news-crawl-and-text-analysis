# -*- coding:utf-8 -*-
# 通用回溯测试框架，支持GetMassBreakAlphaGo和GetMassBreakShape策略
# 功能：在历史数据上运行策略，模拟买入卖出，计算收益指标
from MongoDbComTools.LocalDbTool import LocalDbTool
from MarketPriceSpiderWithScrapy.StockInfoUtils import get_all_stock_code_info_of_cn
import pandas as pd
import numpy as np
import datetime
from typing import List, Tuple, Callable, Dict, Optional
from tqdm import tqdm
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
matplotlib.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

tqdm.pandas(desc="回测进度")


class BacktestResult:
    def __init__(self):
        self.trades = []  # 所有交易记录
        self.total_return = 0.0  # 总收益率
        self.win_rate = 0.0  # 胜率
        self.avg_return = 0.0  # 平均收益率
        self.max_drawdown = 0.0  # 最大回撤
        self.sharpe_ratio = 0.0  # 夏普比率
        self.total_trades = 0  # 总交易次数
        self.win_trades = 0  # 盈利交易次数
        self.loss_trades = 0  # 亏损交易次数
        self.max_profit = 0.0  # 最大单笔盈利
        self.max_loss = 0.0  # 最大单笔亏损


class BacktestFramework:
    """通用回溯测试框架"""
    
    def __init__(self, 
                 strategy_func: Callable,
                 market_type: str = "cn",
                 start_date: str = None,
                 hold_days: int = 30,
                 stop_loss: float = None,
                 take_profit: float = None,
                 min_data_days: int = 60):
        """
        初始化回测框架
        
        Args:
            strategy_func: 策略函数，接受 (stock_code, market, start_date, ave_date, ratio) 参数
            market_type: 市场类型，如 "cn"
            start_date: 回测开始日期，格式 "YYYY-MM-DD"
            hold_days: 默认持有天数
            stop_loss: 止损比例，如 0.1 表示亏损10%止损
            take_profit: 止盈比例，如 0.2 表示盈利20%止盈
            min_data_days: 最少需要的数据天数
        """
        self.strategy_func = strategy_func
        self.market_type = market_type
        self.start_date = start_date
        self.hold_days = hold_days
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.min_data_days = min_data_days
        self.local_db = LocalDbTool()
        self.results = BacktestResult()
    
    def get_stock_data(self, stock_code: str, start_date: str, end_date: str = None):
        """获取股票数据"""
        return self.local_db.get_daily_price_data_of_specific_stock(
            symbol=stock_code,
            market_type=self.market_type,
            start_date=start_date,
            end_date=end_date
        )
    
    def simulate_trade(self, 
                      stock_code: str, 
                      buy_date, 
                      buy_price: float,
                      strategy_params: Dict) -> Optional[Dict]:
        """
        模拟单笔交易
        
        Args:
            stock_code: 股票代码
            buy_date: 买入日期（可以是字符串或datetime对象）
            buy_price: 买入价格
            strategy_params: 策略参数字典，至少包含 ave_date, ratio，
                             也可以包含对单笔交易生效的覆写参数：
                             - hold_days: 覆写默认持有天数
                             - stop_loss: 覆写默认止损
                             - take_profit: 覆写默认止盈
        
        Returns:
            交易结果字典，包含买入卖出信息，如果无法完成交易返回None
        """
        # === 1. 从 strategy_params 中解析本次交易专属的风控参数 ===
        # 如果没有提供，则退回到框架级别的默认配置
        local_hold_days = strategy_params.get("hold_days", self.hold_days) if strategy_params else self.hold_days
        local_stop_loss = strategy_params.get("stop_loss", self.stop_loss) if strategy_params else self.stop_loss
        local_take_profit = strategy_params.get("take_profit", self.take_profit) if strategy_params else self.take_profit

        # 统一处理日期格式
        if isinstance(buy_date, str):
            buy_date_obj = datetime.datetime.strptime(buy_date, "%Y-%m-%d")
            buy_date_str = buy_date
        elif isinstance(buy_date, datetime.datetime):
            buy_date_obj = buy_date
            buy_date_str = buy_date.strftime("%Y-%m-%d")
        elif isinstance(buy_date, datetime.date):
            buy_date_obj = datetime.datetime.combine(buy_date, datetime.time())
            buy_date_str = buy_date.strftime("%Y-%m-%d")
        else:
            # 尝试转换为字符串
            buy_date_str = str(buy_date)
            try:
                buy_date_obj = datetime.datetime.strptime(buy_date_str, "%Y-%m-%d")
            except:
                return None
        
        # 获取买入日期之后的数据（按照当前交易的持有天数取数据）
        end_date_obj = buy_date_obj + datetime.timedelta(days=local_hold_days + 10)  # 多取10天缓冲
        end_date = end_date_obj.strftime("%Y-%m-%d")
        
        res, data = self.get_stock_data(stock_code, buy_date_str, end_date)
        if not res or data.empty:
            return None
        
        # 确保数据按日期排序
        data = data.sort_index()
        
        # 找到买入日期在数据中的位置
        buy_idx = None
        for idx in data.index:
            if isinstance(idx, str):
                try:
                    idx_date = datetime.datetime.strptime(idx, "%Y-%m-%d")
                    if idx_date >= buy_date_obj:
                        buy_idx = idx
                        break
                except:
                    if idx >= buy_date_str:
                        buy_idx = idx
                        break
            elif isinstance(idx, datetime.datetime):
                if idx >= buy_date_obj:
                    buy_idx = idx
                    break
            elif isinstance(idx, datetime.date):
                idx_datetime = datetime.datetime.combine(idx, datetime.time())
                if idx_datetime >= buy_date_obj:
                    buy_idx = idx
                    break
        
        if buy_idx is None:
            return None
        # print(f"buy_idx is {buy_idx}, data is {data}")
        # 获取买入价格（如果未提供，使用买入日期的收盘价）
        if buy_price is None:
            buy_price = data.loc[buy_idx, "close"]
        
        # 模拟持有期间的交易
        buy_position = data.index.get_loc(buy_idx)
        max_position = min(buy_position + local_hold_days, len(data) - 1)
        
        for i in range(buy_position + 1, max_position + 1):
            current_idx = data.index[i]
            current_price = data.loc[current_idx, "close"]
            
            # 计算收益率
            return_rate = (current_price - buy_price) / buy_price
            
            # 检查止损
            if local_stop_loss is not None and return_rate <= -local_stop_loss:
                return {
                    "stock_code": stock_code,
                    "buy_date": buy_date,
                    "sell_date": str(current_idx),
                    "buy_price": buy_price,
                    "sell_price": current_price,
                    "return_rate": return_rate,
                    "hold_days": i - buy_position,
                    "exit_reason": "stop_loss",
                    "strategy_params": strategy_params or {},
                }
            
            # 检查止盈
            if local_take_profit is not None and return_rate >= local_take_profit:
                return {
                    "stock_code": stock_code,
                    "buy_date": buy_date,
                    "sell_date": str(current_idx),
                    "buy_price": buy_price,
                    "sell_price": current_price,
                    "return_rate": return_rate,
                    "hold_days": i - buy_position,
                    "exit_reason": "take_profit",
                    "strategy_params": strategy_params or {},
                }
        
        # 持有到期，使用最后一天的价格
        final_idx = data.index[max_position]
        final_price = data.loc[final_idx, "close"]
        final_return = (final_price - buy_price) / buy_price
        
        return {
            "stock_code": stock_code,
            "buy_date": buy_date,
            "sell_date": str(final_idx),
            "buy_price": buy_price,
            "sell_price": final_price,
            "return_rate": final_return,
            "hold_days": max_position - buy_position,
            "exit_reason": "hold_period",
            "strategy_params": strategy_params or {},
        }
    
    def run_backtest(self, 
                    ave_date: int = 30,
                    ratio: float = 2.0,
                    stock_list: List[str] = None) -> BacktestResult:
        """
        运行回测
        
        Args:
            ave_date: 平均天数
            ratio: 放量倍数
            stock_list: 股票代码列表，如果为None则使用所有A股
        
        Returns:
            BacktestResult对象
        """
        print(f"开始回测，策略参数: ave_date={ave_date}, ratio={ratio}")
        print(f"回测设置: hold_days={self.hold_days}, stop_loss={self.stop_loss}, take_profit={self.take_profit}")
        
        # 获取股票列表
        if stock_list is None:
            stock_info = get_all_stock_code_info_of_cn()
            stock_list = stock_info['joint_quant_code'].tolist()
        
        print(f"待回测股票数量: {len(stock_list)}")
        
        # 对每只股票运行策略并回测
        all_trades = []
        
        for stock_code in tqdm(stock_list, desc="回测进度"):
            try:
                # 运行策略获取突破日期
                strategy_result = self.strategy_func(
                    stock_code, 
                    self.market_type, 
                    self.start_date, 
                    ave_date, 
                    ratio
                )
                # 策略返回格式: (break_dates, price_var, other_metrics...)
                if strategy_result is None or len(strategy_result) == 0:
                    continue
                
                break_dates = strategy_result[0]  # 突破日期列表
                
                if not break_dates or len(break_dates) == 0:
                    continue
                
                # 对每个突破日期进行回测
                for break_date in break_dates:
                    # 统一处理日期格式
                    break_date_str = None
                    if isinstance(break_date, str):
                        break_date_str = break_date
                    elif isinstance(break_date, datetime.datetime):
                        break_date_str = break_date.strftime("%Y-%m-%d")
                    elif isinstance(break_date, datetime.date):
                        break_date_str = break_date.strftime("%Y-%m-%d")
                    else:
                        break_date_str = str(break_date)
                    
                    # 确保突破日期在回测开始日期之后
                    if self.start_date:
                        try:
                            break_date_obj = datetime.datetime.strptime(break_date_str, "%Y-%m-%d")
                            start_date_obj = datetime.datetime.strptime(self.start_date, "%Y-%m-%d")
                            if break_date_obj < start_date_obj:
                                continue
                        except:
                            continue
                    
                    # 模拟交易
                    trade_result = self.simulate_trade(
                        stock_code=stock_code,
                        buy_date=break_date_str,
                        buy_price=None,  # 使用突破日收盘价
                        strategy_params={"ave_date": ave_date, "ratio": ratio, "hold_days": self.hold_days, "stop_loss": self.stop_loss, "take_profit": self.take_profit}
                    )
                    
                    if trade_result:
                        all_trades.append(trade_result)

            except Exception as e:
                # 跳过出错的股票
                continue
        
        # 计算回测指标
        self.results.trades = all_trades
        self.results.total_trades = len(all_trades)
        
        if len(all_trades) == 0:
            print("警告: 没有生成任何交易记录")
            return self.results
        
        # 计算收益指标
        returns = [trade["return_rate"] for trade in all_trades]
        self.results.total_return = np.sum(returns)
        self.results.avg_return = np.mean(returns)
        self.results.win_trades = sum(1 for r in returns if r > 0)
        self.results.loss_trades = sum(1 for r in returns if r <= 0)
        self.results.win_rate = self.results.win_trades / self.results.total_trades if self.results.total_trades > 0 else 0
        self.results.max_profit = max(returns) if returns else 0
        self.results.max_loss = min(returns) if returns else 0
        
        # 计算最大回撤
        cumulative_returns = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = cumulative_returns - running_max
        self.results.max_drawdown = abs(min(drawdowns)) if len(drawdowns) > 0 else 0
        
        # 计算夏普比率（简化版，假设无风险利率为0）
        if len(returns) > 1 and np.std(returns) > 0:
            self.results.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # 年化
        else:
            self.results.sharpe_ratio = 0
        
        return self.results
    
    def generate_report(self, output_file: str = None) -> pd.DataFrame:
        """
        生成回测报告
        
        Args:
            output_file: 输出CSV文件路径
        
        Returns:
            包含详细交易记录的DataFrame
        """
        if len(self.results.trades) == 0:
            print("没有交易记录，无法生成报告")
            return pd.DataFrame()
        
        # 创建交易记录DataFrame
        df = pd.DataFrame(self.results.trades)
        # 打印汇总统计
        print("\n" + "="*60)
        print("回测结果汇总")
        print(df)
        print("="*60)
        print(f"总交易次数: {self.results.total_trades}")
        print(f"盈利交易: {self.results.win_trades}")
        print(f"亏损交易: {self.results.loss_trades}")
        print(f"胜率: {self.results.win_rate:.2%}")
        print(f"平均收益率: {self.results.avg_return:.2%}")
        print(f"最大单笔盈利: {self.results.max_profit:.2%}")
        print(f"最大单笔亏损: {self.results.max_loss:.2%}")
        print(f"最大回撤: {self.results.max_drawdown:.2%}")
        print(f"夏普比率: {self.results.sharpe_ratio:.2f}")
        print("="*60)
        
        # 按退出原因统计
        if "exit_reason" in df.columns:
            exit_stats = df.groupby("exit_reason").agg({
                "return_rate": ["count", "mean", "sum"]
            })
            print("\n按退出原因统计:")
            print(exit_stats)
        
        # 保存到文件
        if output_file:
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n详细交易记录已保存到: {output_file}")
        
        return df
    
    def plot_results(self, save_path: str = None):
        """绘制回测结果图表"""
        if len(self.results.trades) == 0:
            print("没有交易记录，无法绘图")
            return
        
        df = pd.DataFrame(self.results.trades)
        
        # 创建图表
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. 收益率分布直方图
        axes[0, 0].hist(df["return_rate"], bins=50, edgecolor='black')
        axes[0, 0].axvline(0, color='r', linestyle='--', label='盈亏平衡线')
        axes[0, 0].set_xlabel('收益率')
        axes[0, 0].set_ylabel('频数')
        axes[0, 0].set_title('收益率分布')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 累计收益曲线
        df_sorted = df.sort_values("buy_date")
        cumulative_returns = df_sorted["return_rate"].cumsum()
        axes[0, 1].plot(range(len(cumulative_returns)), cumulative_returns)
        axes[0, 1].axhline(0, color='r', linestyle='--')
        axes[0, 1].set_xlabel('交易序号')
        axes[0, 1].set_ylabel('累计收益率')
        axes[0, 1].set_title('累计收益曲线')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 持有天数分布
        if "hold_days" in df.columns:
            axes[1, 0].hist(df["hold_days"], bins=20, edgecolor='black')
            axes[1, 0].set_xlabel('持有天数')
            axes[1, 0].set_ylabel('频数')
            axes[1, 0].set_title('持有天数分布')
            axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 按退出原因统计
        if "exit_reason" in df.columns:
            exit_counts = df["exit_reason"].value_counts()
            axes[1, 1].bar(exit_counts.index, exit_counts.values)
            axes[1, 1].set_xlabel('退出原因')
            axes[1, 1].set_ylabel('交易次数')
            axes[1, 1].set_title('退出原因统计')
            axes[1, 1].tick_params(axis='x', rotation=45)
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        else:
            plt.show()


def strategy_adapter_alphago(stock_code: str, market: str, start: str, ave_date: int, ratio: float):
    """适配GetMassBreakAlphaGo策略"""
    from MassBreak.GetMassBreakAlphaGo import getVolumeBreakDateList
    return getVolumeBreakDateList(stock_code, market, start, ave_date, ratio)


def strategy_adapter_shape(stock_code: str, market: str, start: str, ave_date: int, ratio: float):
    """适配GetMassBreakShape策略"""
    from MassBreak.GetMassBreakShape import getVolumeBreakDateList
    return getVolumeBreakDateList(stock_code, market, start, ave_date, ratio)

if __name__ == "__main__":
    import sys
    
    # 示例用法
    if len(sys.argv) < 6:
        print("用法: python BacktestFramework.py <策略类型> <市场类型> <开始日期> <平均天数> <放量倍数> [持有天数] [止损] [止盈]")
        print("策略类型: alphago 或 shape")
        print("示例: python BacktestFramework.py alphago cn 2024-01-01 30 2.0 30 0.1 0.2")
        sys.exit(1)
    
    strategy_type = sys.argv[1]  # "alphago" 或 "shape"
    market_type = sys.argv[2]
    start_date = sys.argv[3]
    ave_date = int(sys.argv[4])
    ratio = float(sys.argv[5])
    hold_days = int(sys.argv[6]) if len(sys.argv) > 6 else 30
    stop_loss = float(sys.argv[7]) if len(sys.argv) > 7 else None
    take_profit = float(sys.argv[8]) if len(sys.argv) > 8 else None
    
    # 选择策略
    if strategy_type == "alphago":
        strategy_func = strategy_adapter_alphago
    elif strategy_type == "shape":
        strategy_func = strategy_adapter_shape
    else:
        print(f"未知策略类型: {strategy_type}")
        sys.exit(1)
    
    # 创建回测框架
    backtest = BacktestFramework(
        strategy_func=strategy_func,
        market_type=market_type,
        start_date=start_date,
        hold_days=hold_days,
        stop_loss=stop_loss,
        take_profit=take_profit
    )
    
    # 运行回测
    results = backtest.run_backtest(ave_date=ave_date, ratio=ratio, stock_list=["sh600938"])#, "sh600938", "sz000547"])
    
    # 生成报告
    output_file = f"backtest_{strategy_type}_{market_type}_{start_date}_{ave_date}_{ratio}.csv"
    backtest.generate_report(output_file=output_file)
    
    # 绘制图表
    plot_file = f"backtest_{strategy_type}_{market_type}_{start_date}_{ave_date}_{ratio}.png"
    backtest.plot_results(save_path=plot_file)
