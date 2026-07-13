"""WebRTC signaling and camera-track regression tests."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

from aioice import stun
from aiortc import RTCPeerConnection
from PIL import Image

from webrtc import config, main


def test_offer_delivers_camera_video_track(tmp_path, monkeypatch):
    image_path = tmp_path / "camera.jpg"
    Image.new("RGB", (640, 360), color=(10, 30, 50)).save(image_path)
    state_path = tmp_path / "camera-slots.json"
    state_path.write_text(json.dumps([
        {"slotId": 1, "sourceType": "IMAGE", "path": str(image_path), "deviceIndex": 0},
        {"slotId": 2, "sourceType": "OFF", "path": None, "deviceIndex": 0},
        {"slotId": 3, "sourceType": "OFF", "path": None, "deviceIndex": 0},
    ]), encoding="utf-8")
    monkeypatch.setattr(config, "CAMERA_STATE_FILE", state_path)
    monkeypatch.setattr(config, "CAMERA_FRAME_DIR", tmp_path / "frames")
    monkeypatch.setattr(main, "registry", main.CameraRegistry())

    async def exercise():
        client = RTCPeerConnection()
        source_track = await main.registry.subscribe(1)
        source_frame = await asyncio.wait_for(source_track.recv(), timeout=5)
        assert source_frame.width == 640
        assert source_frame.height == 360
        for _ in range(20):
            if (config.CAMERA_FRAME_DIR / "camera-1.jpg").is_file():
                break
            await asyncio.sleep(0.05)
        assert (config.CAMERA_FRAME_DIR / "camera-1.jpg").is_file()
        client.addTransceiver("video", direction="recvonly")
        local_offer = await client.createOffer()
        await client.setLocalDescription(local_offer)
        answer = await main.offer(1, {
            "type": client.localDescription.type,
            "sdp": client.localDescription.sdp,
        }, SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")))
        assert answer["type"] == "answer"
        assert "m=video" in answer["sdp"]
        await main.close_peer(answer["sessionId"])
        await client.close()
        await main.registry.close()

    asyncio.run(exercise())


def test_unconnected_offer_is_expired(monkeypatch):
    closed = []

    async def fake_close(session_id):
        closed.append(session_id)
        main.peer_connections.pop(session_id, None)
    main.peer_connections["stale-session"] = SimpleNamespace(connectionState="new")
    monkeypatch.setattr(main, "close_peer", fake_close)
    asyncio.run(main.expire_unconnected_peer("stale-session", timeout_seconds=0))
    assert closed == ["stale-session"]


def test_client_id_is_bounded_before_session_tracking():
    value = "x" * 500
    assert len(str(value)[:128]) == 128


def test_mdns_candidate_uses_signaling_client_ip():
    sdp = "a=candidate:1 1 udp 123 browser-id.local 45678 typ host\r\n"

    rewritten = main.expose_mdns_candidates(sdp, "100.119.32.60")

    assert "100.119.32.60 45678 typ host" in rewritten
    assert ".local" not in rewritten


def test_stun_binding_returns_observed_address():
    sent = []

    class Transport:
        def sendto(self, data, address):
            sent.append((data, address))

    protocol = main.StunBindingProtocol()
    protocol.connection_made(Transport())
    request = stun.Message(stun.Method.BINDING, stun.Class.REQUEST)
    protocol.datagram_received(bytes(request), ("100.119.32.60", 45678))

    assert len(sent) == 1
    response = stun.parse_message(sent[0][0])
    assert response.message_class == stun.Class.RESPONSE
    assert response.attributes["XOR-MAPPED-ADDRESS"] == ("100.119.32.60", 45678)


def test_ice_config_issues_valid_temporary_turn_credential(monkeypatch):
    monkeypatch.setattr(config, "TURN_SECRET", "test-shared-secret")
    monkeypatch.setattr(config, "PUBLIC_HOST", "100.73.64.55")
    monkeypatch.setattr(config, "TURN_PORT", 3478)
    monkeypatch.setattr(config, "TURN_TTL_SECONDS", 3600)
    monkeypatch.setattr(config, "TURN_FORCE_RELAY", True)

    result = asyncio.run(main.ice_config())

    server = result["iceServers"][0]
    expected = base64.b64encode(hmac.new(
        b"test-shared-secret",
        server["username"].encode("utf-8"),
        hashlib.sha1,
    ).digest()).decode("ascii")
    assert result["iceTransportPolicy"] == "relay"
    assert result["expiresAt"] > int(time.time())
    assert server["credential"] == expected
    assert server["urls"][0] == "turn:100.73.64.55:3478?transport=tcp"


def test_codec_preferences_are_limited_to_vp8():
    async def exercise():
        pc = RTCPeerConnection()
        transceiver = pc.addTransceiver("video", direction="recvonly")

        main.prefer_vp8(pc)

        assert transceiver._preferred_codecs
        assert {codec.mimeType.lower() for codec in transceiver._preferred_codecs} == {"video/vp8"}
        await pc.close()

    asyncio.run(exercise())


def test_bounded_track_returns_an_independent_frame():
    class Source:
        async def recv(self):
            return main.VideoFrame.from_ndarray(
                main.np.zeros((24, 32, 3), dtype=main.np.uint8),
                format="rgb24",
            )

    async def exercise():
        source = Source()
        original = await source.recv()

        class ExactSource:
            async def recv(self):
                return original

        copied = await main.BoundedVideoTrack(ExactSource()).recv()
        assert copied is not original
        assert copied.width == original.width
        assert copied.height == original.height

    asyncio.run(exercise())
