"""车牌接口并发回归测试。"""
import asyncio
from threading import Barrier

import httpx

from license import main


def test_image_requests_are_offloaded_concurrently(monkeypatch):
    barrier = Barrier(4, timeout=2)

    class FakePipeline:
        def process(self, _image_url, _include_visuals=True):
            barrier.wait()
            return {"detections": [], "detectionCount": 0}

    monkeypatch.setattr(main, "_pipeline", FakePipeline())

    async def invoke():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await asyncio.gather(*(
                client.post("/api/v1/inference/image", json={
                    "task_type": "license_plate",
                    "image_url": f"test-{index}.png",
                })
                for index in range(4)
            ))
        assert all(response.status_code == 200 for response in responses)

    asyncio.run(invoke())


def test_image_path_request_can_enable_visuals(monkeypatch):
    received = {}

    class FakePipeline:
        def process(self, image_url, include_visuals=True):
            received["image_url"] = image_url
            received["include_visuals"] = include_visuals
            return {
                "detections": [],
                "detectionCount": 0,
                "annotatedImageUrl": "data:image/jpeg;base64,test",
            }

    monkeypatch.setattr(main, "_pipeline", FakePipeline())

    async def invoke():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/inference/image", json={
                "task_type": "license_plate",
                "image_path": "/tmp/camera-1.jpg",
                "include_visuals": True,
            })
        assert response.status_code == 200
        assert response.json()["data"]["annotatedImageUrl"].startswith("data:image/jpeg")

    asyncio.run(invoke())
    assert received == {
        "image_url": "/tmp/camera-1.jpg",
        "include_visuals": True,
    }
