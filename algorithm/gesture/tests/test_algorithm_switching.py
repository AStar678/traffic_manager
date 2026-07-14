from __future__ import annotations

import json

import numpy as np

from gesture.service import GestureRecognitionService
from gesture_dinov2_tcn.runtime import (
    DINO_ALGORITHM_ID,
    LEGACY_ALGORITHM_ID,
    Dinov2TcnPrototypeRuntime,
    VideoSample,
)


def _sample_decoder(payload):
    value = float(payload.get("value", 0.0))
    return VideoSample(
        frame=np.full((8, 8, 3), value, dtype=np.uint8),
        geometry=np.full(175, value / 255.0, dtype=np.float32),
        detected=1.0,
    )


def _encoder(samples):
    embedding = np.zeros(128, dtype=np.float32)
    embedding[0] = np.mean([sample.frame.mean() for sample in samples]) / 255.0
    embedding[1] = 1.0
    return embedding


def test_algorithms_keep_independent_prototype_stores(tmp_path):
    legacy_store = tmp_path / "legacy.json"
    legacy_store.write_text(
        json.dumps([
            {
                "id": "legacy-one",
                "name": "旧算法手势",
                "kind": "static",
                "vector": [1.0, 0.0],
                "sequence": [[1.0, 0.0]],
            }
        ], ensure_ascii=False),
        encoding="utf-8",
    )
    service = GestureRecognitionService(
        tmp_path / "config.json",
        legacy_store,
        tmp_path / "unused.pt",
        tmp_path / "deep.json",
    )
    service.deep_runtime = Dinov2TcnPrototypeRuntime(
        tmp_path / "unused.pt",
        tmp_path / "deep.json",
        encoder=_encoder,
        sample_decoder=_sample_decoder,
    )

    selected = service.select_algorithm(DINO_ALGORITHM_ID)
    assert selected["algorithm"]["active"] == DINO_ALGORITHM_ID
    assert selected["config"]["sampleTarget"] == 12

    service.start_recording({"name": "视频挥手", "kind": "dynamic", "holdMs": 1})
    result = None
    for value in range(12):
        result = service.process_payload({"type": "frame", "value": value})
    assert result["recordingComplete"]["name"] == "视频挥手"
    deep_prototypes = service.list_prototypes()["prototypes"]
    assert len(deep_prototypes) == 6
    assert len([item for item in deep_prototypes if item.get("source") == "built_in"]) == 5
    assert len([item for item in deep_prototypes if item.get("source") == "custom"]) == 1

    recognized = service.process_payload({"type": "frame", "value": 11})["recognition"]
    assert recognized["accepted"] is True
    assert recognized["name"] == "视频挥手"

    service.select_algorithm(LEGACY_ALGORITHM_ID)
    assert [item["id"] for item in service.list_prototypes()["prototypes"]] == ["legacy-one"]
    assert json.loads(legacy_store.read_text(encoding="utf-8"))[0]["name"] == "旧算法手势"
