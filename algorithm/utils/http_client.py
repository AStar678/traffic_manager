"""HTTP客户端：回调Java后端"""
import httpx

async def callback_result(callback_url: str, data: dict):
    """将实时结果回调给Java后端"""
    async with httpx.AsyncClient() as client:
        await client.post(callback_url, json=data)
