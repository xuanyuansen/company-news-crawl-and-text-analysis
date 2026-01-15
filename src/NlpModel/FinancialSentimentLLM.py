import re
from vllm import LLM, SamplingParams

class FinancialSentimentLLM:
    """
    根据显存情况看使用哪个模型
    测试Qwen3-8B-AWQ、Qwen3-14B-AWQ都不错
    """
    _instance = None  # 类变量，存储单例
    # 避免多进程开启多个LLM
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FinancialSentimentLLM, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, model_path, tp_size=2):
        # 如果已经加载过模型，直接退出，不要重复加载
        if self._initialized: return

        self.model_path = model_path
        self.tp_size = tp_size # 启动GPU个数
        self.llm = None
        self.sampling_params = SamplingParams(
            temperature=0.6,  
            top_p=0.8,
            max_tokens=256
        )
        self.llm = LLM(
                model=self.model_path,
                tensor_parallel_size=self.tp_size,
                quantization="awq",
                dtype="auto",
                max_model_len=4096,
                gpu_memory_utilization=0.8
            )
        self._initialized = True


    def predict_score(self, article):
        """执行推理获取分值"""
        if len(article) > 4000:
            article = article[0:4000]

        prompt = f"""<|im_start|>user
你是一个资深的金融量化分析师，你的任务是对下面的文章进行打分，判断其利好的概率
文章: {article}
分值在0-1之间，越高代表利好的概率越大。
回答格式要求：
1.使用json输出结果，且json中只包含一个字段label
2.格式举例：{{"label":0.5}} .<|im_end|>
<|im_start|>assistant
<think>
</think>
Answer:
"""
        outputs = self.llm.generate([prompt], self.sampling_params)
        res_text = outputs[0].outputs[0].text
        
        try:
            # 使用正则匹配 json 中的数字
            match = re.search(r'"label":\s*([\d.]+)', res_text)
            if match:
                label = float(match.group(1))
                if label > 0.5:
                    return '利好',label
                else:
                    return '利空',1-label
            return'利好',0.5
        except Exception as e:
            print(f"解析失败: {e}")
            return '利好',0.5