from typing import Dict, Optional, Union
import json
import requests
from loguru import logger
from requests.exceptions import RequestException, ProxyError

class HTTPClient:
    """HTTP客户端基类"""
    
    def __init__(self, base_url: str, proxies: Optional[Dict[str, str]] = None):
        """
        初始化HTTP客户端
        :param base_url: API基础URL
        :param proxies: 代理设置
        """
        self.base_url = base_url.rstrip('/')  # 移除末尾的斜杠
        self.proxies = proxies
        self.session = requests.Session()
        
    def _prepare_url(self, path: str) -> str:
        """
        准备完整的URL
        :param path: API路径
        :return: 完整的URL
        """
        path = path.lstrip('/')  # 移除开头的斜杠
        return f"{self.base_url}/{path}"
        
    def _prepare_request_kwargs(self, 
                              headers: Optional[Dict] = None,
                              params: Optional[Dict] = None,
                              data: Optional[Union[Dict, str]] = None,
                              timeout: int = 10,
                              **kwargs) -> Dict:
        """
        准备请求参数
        """
        request_kwargs = {
            'headers': headers or {},
            'verify': True,
            'timeout': timeout,
            **kwargs
        }
        
        if self.proxies:
            request_kwargs['proxies'] = self.proxies
            
        if params:
            request_kwargs['params'] = params
            
        if data:
            if isinstance(data, dict):
                request_kwargs['json'] = data
            else:
                request_kwargs['data'] = data
                
        return request_kwargs
        
    def request(self,
                method: str,
                path: str,
                headers: Optional[Dict] = None,
                params: Optional[Dict] = None,
                data: Optional[Union[Dict, str]] = None,
                timeout: int = 10,
                **kwargs) -> Dict:
        """
        发送HTTP请求
        :param method: 请求方法（GET, POST等）
        :param path: API路径
        :param headers: 请求头
        :param params: URL参数
        :param data: 请求体数据
        :param timeout: 超时时间（秒）
        :return: 响应数据
        """
        url = self._prepare_url(path)
        request_kwargs = self._prepare_request_kwargs(
            headers=headers,
            params=params,
            data=data,
            timeout=timeout,
            **kwargs
        )
        
        # 记录请求信息
        logger.debug(f"发送请求: {method} {url}")
        if params:
            logger.debug(f"查询参数: {params}")
        if data:
            logger.debug(f"请求数据: {data}")
            
        try:
            response = self.session.request(method, url, **request_kwargs)
            response.raise_for_status()
            
            # 尝试解析JSON响应
            try:
                data = response.json()
                logger.debug(f"API响应: {data}")
                return data
            except json.JSONDecodeError:
                logger.warning(f"响应不是有效的JSON格式: {response.text}")
                return {"error": "Invalid JSON response"}
                
        except ProxyError as e:
            logger.error(f"代理连接错误: {str(e)}")
            return {"error": f"Proxy error: {str(e)}"}
        except RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            return {"error": f"Unknown error: {str(e)}"}
            
    def get(self, path: str, **kwargs) -> Dict:
        """发送GET请求"""
        return self.request('GET', path, **kwargs)
        
    def post(self, path: str, **kwargs) -> Dict:
        """发送POST请求"""
        return self.request('POST', path, **kwargs)
        
    def put(self, path: str, **kwargs) -> Dict:
        """发送PUT请求"""
        return self.request('PUT', path, **kwargs)
        
    def delete(self, path: str, **kwargs) -> Dict:
        """发送DELETE请求"""
        return self.request('DELETE', path, **kwargs) 