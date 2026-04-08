import re
import platform
from typing import Any

class FinancialSentimentLLM:
    """
    根据显存情况看使用哪个模型
    GPU版本测试Qwen3-8B-AWQ、Qwen3-14B-AWQ都不错
    CPU版本为了保持速度及安装方便使用transformers 部署Qwen3-4B
    """
    _instance = None  # 类变量，存储单例
    # 避免多进程开启多个LLM
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FinancialSentimentLLM, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        model_path: str,
        tp_size: int = 2,
        use_device_type: str = "gpu",
        ollama_model: str = "qwen3:1.7b",
    ):
        # 如果已经加载过模型，直接退出，不要重复加载
        if self._initialized:
            return

        self.model_path = model_path
        self.tp_size = tp_size  # 启动GPU个数
        self.use_device_type = use_device_type.lower()
        self.system_name = platform.system()
        self.runtime_backend = None
        self.llm: Any = None
        self.sampling_params: Any = None
        self.tokenizer: Any = None
        self.torch: Any = None
        self.ollama_client: Any = None
        self.max_tokens = 1024
        self.temperature = 0.6
        self.top_p = 0.8
        self.ollama_base_url = "http://localhost:11434/v1"
        self.ollama_api_key = "ollama"
        self.ollama_model = ollama_model
        self.ollama_temperature = 0.3
        self.ollama_top_p = 0.9
        self.ollama_max_tokens = 30

        if self.system_name == "Darwin":
            self.runtime_backend = "ollama"
        elif self.use_device_type == "gpu":
            self.runtime_backend = "gpu"
        elif self.use_device_type == "cpu":
            self.runtime_backend = "cpu"
        else:
            raise ValueError(
                f"use_device_type 仅支持 'cpu' 或 'gpu'，当前值: {use_device_type}"
            )

        if self.runtime_backend == "gpu":
            from vllm import LLM, SamplingParams

            self.sampling_params = SamplingParams(
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.max_tokens,
            )
            self.llm = LLM(
                model=self.model_path,
                tensor_parallel_size=self.tp_size,
                # quantization="awq",
                dtype="auto",
                max_model_len=4096,
                gpu_memory_utilization=0.8,
            )
        elif self.runtime_backend == "cpu":
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self.torch = torch
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, trust_remote_code=True
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.llm = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                torch_dtype=torch.bfloat16,
            )
            self.llm.to("cpu")
            self.llm.eval()
            self.llm.config.use_cache = True
        else:
            from openai import OpenAI

            self.ollama_client = OpenAI(
                base_url=self.ollama_base_url,
                api_key=self.ollama_api_key,
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
1.回答简洁不需要进行思考。
2.使用json输出结果，且json中只包含一个字段label
3.格式举例：{{"label":0.5}} .<|im_end|>
<|im_start|>assistant
<think>
</think>
Answer:
"""
        try:
            if self.runtime_backend == "ollama":
                response = self.ollama_client.chat.completions.create(
                    model=self.ollama_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.ollama_temperature,
                    top_p=self.ollama_top_p,
                    max_tokens=self.ollama_max_tokens,
                )
                res_text = response.choices[0].message.content or ""
            elif self.runtime_backend == "gpu":
                outputs = self.llm.generate([prompt], self.sampling_params)
                res_text = outputs[0].outputs[0].text
            else:
                inputs = self.tokenizer(prompt, return_tensors="pt")
                inputs = {k: v.to("cpu") for k, v in inputs.items()}
                with self.torch.inference_mode():
                    outputs = self.llm.generate(
                        **inputs,
                        max_new_tokens=self.max_tokens,
                        do_sample=True,
                        temperature=self.temperature,
                        top_p=self.top_p,
                        use_cache=True,
                        pad_token_id=self.tokenizer.pad_token_id,
                    )
                generated_tokens = outputs[0][inputs["input_ids"].shape[-1] :]
                res_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)

            # 使用正则匹配 json 中的数字
            match = re.search(r'"label":\s*([\d.]+)', res_text)
            if match:
                label = float(match.group(1))
                if label > 0.5:
                    return '利好', label
                else:
                    return '利空', 1-label
            return '利好', 0.5
        except Exception as e:
            print(f"解析失败: {e}")
            return '利好', 0.5
