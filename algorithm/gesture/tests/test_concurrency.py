"""车主手势只读识别接口并发回归测试。"""
import asyncio
from threading import Barrier

import httpx

from gesture import api, main


def test_recognize_requests_are_offloaded_concurrently(monkeypatch):
    barrier = Barrier(4, timeout=2)

    def recognize(_payload):
        barrier.wait()
        return {"recognition": {"accepted": False}}

    monkeypatch.setattr(api.gesture_service, "recognize", recognize)

    async def invoke():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await asyncio.gather(*(
                client.post("/api/v1/owner-gestures/recognize", json={"vector": [index] * 75})
                for index in range(4)
            ))
        assert all(response.status_code == 200 for response in responses)

    asyncio.run(invoke())
