import unittest
import requests
import json
import time
from datetime import datetime

class TestOllamaAPI(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        self.base_url = "http://localhost:11434/api"
        self.model = "deepseek-r1:8b"  # 更新为实际安装的模型名称
        
    def test_model_connection(self):
        """测试模型连接是否正常"""
        try:
            # 测试模型列表API
            response = requests.get(f"{self.base_url}/tags")
            self.assertEqual(response.status_code, 200)
            print("可用模型列表:", response.json())
            
            # 确认模型是否存在
            models = response.json()['models']
            model_names = [model['name'] for model in models]
            print(f"已安装的模型: {model_names}")
            self.assertIn(self.model, model_names, f"{self.model} 模型未找到")
            
        except requests.exceptions.ConnectionError:
            self.fail("无法连接到Ollama服务，请确保服务已启动")
            
    def test_simple_generation(self):
        """测试简单的代码生成"""
        prompt = "Write a Python function to calculate fibonacci sequence"
        
        try:
            response = requests.post(
                f"{self.base_url}/generate",  # 使用generate端点
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            self.assertEqual(response.status_code, 200)
            result = response.json()
            print("\n生成的响应:")
            print(result)
            
        except requests.exceptions.RequestException as e:
            self.fail(f"API请求失败: {str(e)}")
            
    def test_market_analysis(self):
        """测试市场分析场景"""
        market_data = {
            "current_price": 45000,
            "24h_high": 46000,
            "24h_low": 44000,
            "volume": 1000,
            "position": 0.1
        }
        
        json_template = '''
{
    "analysis": "市场分析内容",
    "recommendation": "BUY/SELL/HOLD",
    "quantity": 0.01,
    "confidence": 0.8
}
'''
        
        prompt = f"""
作为一个交易专家，请分析以下市场数据并给出交易建议：
当前价格: ${market_data['current_price']}
24小时最高: ${market_data['24h_high']}
24小时最低: ${market_data['24h_low']}
成交量: {market_data['volume']}
当前持仓: {market_data['position']} BTC

请提供：
1. 市场分析
2. 交易建议（买入/卖出/持有）
3. 建议交易数量
4. 信心水平（0-1）

请用以下JSON格式回复：
{json_template}
"""
        
        try:
            response = requests.post(
                f"{self.base_url}/generate",  # 使用generate端点
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            self.assertEqual(response.status_code, 200)
            result = response.json()
            print("\n市场分析响应:")
            print(result)
            
        except requests.exceptions.RequestException as e:
            self.fail(f"API请求失败: {str(e)}")

    def test_generation_speed(self):
        """测试模型生成速度"""
        # 准备不同长度的提示词进行测试
        test_prompts = [
            "计算1+1等于几?",  # 短文本
            "请用Python写一个冒泡排序算法",  # 中等文本
            """请分析以下市场情况并给出建议：
            比特币当前价格45000美元，24小时内最高46000美元，最低44000美元。
            市场成交量较昨日上升15%，主要技术指标RSI为65，MACD显示金叉。
            目前持仓0.1 BTC，请给出是否应该继续持有、加仓或者卖出的建议。
            请详细解释你的分析过程和推荐理由。""",  # 长文本
        ]
        
        print("\n生成速度测试结果:")
        print("-" * 50)
        print("| 提示词长度 | 响应长度 | 生成时间 | 速度(token/s) |")
        print("-" * 50)
        
        for prompt in test_prompts:
            try:
                start_time = time.time()
                
                response = requests.post(
                    f"{self.base_url}/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                
                end_time = time.time()
                generation_time = end_time - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('response', '')
                    
                    # 简单估算token数量（中文按字符计算，英文按空格分词）
                    prompt_tokens = len(prompt)
                    response_tokens = len(response_text)
                    total_tokens = prompt_tokens + response_tokens
                    
                    # 计算生成速度
                    tokens_per_second = total_tokens / generation_time if generation_time > 0 else 0
                    
                    print(f"| {prompt_tokens:^10d} | {response_tokens:^8d} | {generation_time:^8.2f}s | {tokens_per_second:^12.2f} |")
                    
                    # 打印详细响应
                    print(f"\n提示词: {prompt[:50]}...")
                    print(f"响应: {response_text[:100]}...")
                    print("-" * 50)
                    
                else:
                    print(f"请求失败，状态码: {response.status_code}")
                    
            except Exception as e:
                print(f"测试出错: {str(e)}")
                
            # 在测试之间添加短暂延迟，避免请求过于频繁
            time.sleep(1)

if __name__ == '__main__':
    unittest.main() 