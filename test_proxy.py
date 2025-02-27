import aiohttp
import asyncio
import ssl
import certifi

async def test_proxy():
    # 创建SSL上下文
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    # 代理配置
    proxy = "http://127.0.0.1:7890"
    
    try:
        async with aiohttp.ClientSession() as session:
            # 测试市场数据API
            url = "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"
            print(f"正在测试: {url}")
            print(f"使用代理: {proxy}")
            
            async with session.get(
                url,
                proxy=proxy,
                ssl=ssl_context
            ) as response:
                print(f"状态码: {response.status}")
                text = await response.text()
                print(f"响应内容: {text[:200]}...")  # 只显示前200个字符
                
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_proxy()) 