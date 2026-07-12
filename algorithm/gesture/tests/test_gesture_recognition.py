"""Gesture recognition replacement smoke tests."""

from gesture.engine import create_recognition_engine, enroll_vectors, process_frame


def test_enroll_and_process_static_vector():
    engine = create_recognition_engine([], None)
    vector = [0.0] * 75

    gesture = enroll_vectors(
        engine,
        {"name": "测试手势", "action": "wake", "kind": "static", "holdMs": 100},
        [vector for _ in range(3)],
    )

    assert gesture["name"] == "测试手势"
    result = process_frame(engine, vector, now=1000)
    assert result["prototypes"][0]["name"] == "测试手势"
