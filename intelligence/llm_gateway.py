# intelligence/llm_gateway.py
import os
import requests
import json

class LLMError(Exception):
    """通用 LLM 错误"""
    pass

class PaymentRequired(LLMError):
    """需要付费 / 额度不足"""
    pass

class AuthenticationError(LLMError):
    """认证错误"""
    pass

class ServiceUnavailable(LLMError):
    """服务不可达"""
    pass

class LLMGateway:
    def __init__(self, model='deepseek'):
        self.model = model
        if model == 'deepseek':
            self.api_key = os.getenv('DEEPSEEK_API_KEY')
            self.url = 'https://api.deepseek.com/v1/chat/completions'
        elif model == 'qwen':
            self.api_key = os.getenv('DASHSCOPE_API_KEY')
            self.url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'
        elif model == 'ollama':
            self.url = 'http://localhost:11434/api/chat'
            self.api_key = None
        else:
            raise ValueError(f"不支持的模型: {model}")

    def chat(self, messages, temperature=0.7, max_tokens=2000):
        if self.model == 'deepseek':
            return self._call_deepseek(messages, temperature, max_tokens)
        elif self.model == 'qwen':
            return self._call_qwen(messages, temperature, max_tokens)
        elif self.model == 'ollama':
            return self._call_ollama(messages, temperature, max_tokens)

    def _call_deepseek(self, messages, temperature, max_tokens):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': 'deepseek-chat',
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        try:
            resp = requests.post(self.url, json=data, headers=headers)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 402:
                raise PaymentRequired("DeepSeek 账户余额不足，请充值")
            elif status == 401:
                raise AuthenticationError("DeepSeek API Key 无效")
            else:
                raise ServiceUnavailable(f"DeepSeek 服务异常: {status}")
        except requests.exceptions.ConnectionError:
            raise ServiceUnavailable("无法连接 DeepSeek 服务")
        return resp.json()['choices'][0]['message']['content']

    def _call_qwen(self, messages, temperature, max_tokens):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': 'qwen-turbo',
            'input': {'messages': messages},
            'parameters': {
                'temperature': temperature,
                'max_tokens': max_tokens
            }
        }
        try:
            resp = requests.post(self.url, json=data, headers=headers)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 402:
                raise PaymentRequired("通义千问 账户余额不足")
            elif status == 401:
                raise AuthenticationError("通义千问 API Key 无效")
            else:
                raise ServiceUnavailable(f"通义千问 服务异常: {status}")
        except requests.exceptions.ConnectionError:
            raise ServiceUnavailable("无法连接 通义千问 服务")
        return resp.json()['output']['text']

    def _call_ollama(self, messages, temperature, max_tokens):
        # 使用本地已下载的 gemma3:4b 模型，稳定性远高于 qwen:0.5b
        data = {
            'model': 'gemma3:4b',
            'messages': messages,
            'stream': False,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens
            }
        }
        try:
            resp = requests.post(self.url, json=data)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ServiceUnavailable(f"Ollama 服务异常: {e.response.status_code}")
        except requests.exceptions.ConnectionError:
            raise ServiceUnavailable("无法连接 Ollama 服务，请确认已启动 ollama serve")
        return resp.json()['message']['content']