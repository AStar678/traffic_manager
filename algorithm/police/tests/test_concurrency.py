"""交警手势接口并发回归测试。"""
import asyncio
from threading import Barrier

import httpx

from police import main


def test_image_requests_are_offloaded_concurrently(monkeypatch):
    barrier = Barrier(4, timeout=2)

    class FakePipeline:
        def process(self, _image_url, _include_visuals=True, _source_id="default"):
            barrier.wait()
            return {"detections": [], "detectionCount": 0}

    monkeypatch.setattr(main, "_pipeline", FakePipeline())

    async def invoke():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await asyncio.gather(*(
                client.post("/api/v1/inference/image", json={
                    "task_type": "police_gesture",
                    "image_url": f"test-{index}.png",
                })
                for index in range(4)
            ))
        assert all(response.status_code == 200 for response in responses)

    asyncio.run(invoke())
