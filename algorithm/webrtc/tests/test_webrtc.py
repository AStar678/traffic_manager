"""WebRTC signaling and camera-track regression tests."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
from fractions import Fraction
from types import SimpleNamespace

from aioice import stun
from aiortc import RTCPeerConnection
from fastapi import HTTPException
from PIL import Image

from webrtc import config, main


def test_offer_delivers_camera_video_track(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ENABLE_WEBRTC", True)
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
        assert source_frame.width == 720
        assert source_frame.height == 480
        for _ in range(20):
            if (
                (config.CAMERA_FRAME_DIR / "camera-1.jpg").is_file()
                and (config.CAMERA_FRAME_DIR / "camera-1.display.jpg").is_file()
            ):
                break
            await asyncio.sleep(0.05)
        assert (config.CAMERA_FRAME_DIR / "camera-1.jpg").is_file()
        with Image.open(config.CAMERA_FRAME_DIR / "camera-1.jpg") as snapshot:
            assert snapshot.size == (640, 360)
        with Image.open(config.CAMERA_FRAME_DIR / "camera-1.display.jpg") as display:
            assert display.size == (720, 480)
        client.addTransceiver("video", direction="recvonly")
        local_offer = await client.createOffer()
        await client.setLocalDescription(local_offer)
        answer = await main.offer(1, {
            "type": client.localDescription.type,
            "sdp": client.localDescription.sdp,
            "delayMs": 1000,
        }, SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")))
        assert answer["type"] == "answer"
        assert answer["delayMs"] == 1000
        assert "m=video" in answer["sdp"]
        await main.close_peer(answer["sessionId"])
        await client.close()
        await main.registry.close()

    asyncio.run(exercise())


def test_static_image_track_uses_configured_output_clock(monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_FPS", 20)

    async def exercise():
        track = main.StaticImageTrack.__new__(main.StaticImageTrack)
        main.VideoStreamTrack.__init__(track)
        track.frame = main.VideoFrame.from_ndarray(
            main.np.zeros((24, 32, 3), dtype=main.np.uint8), format="rgb24"
        )
        track._started_at = asyncio.get_running_loop().time() - 1
        track._frame_index = 0
        track._pts_step = 4_500
        track._time_base = Fraction(1, 90_000)

        first = await track.recv()
        second = await track.recv()

        assert first.pts == 0
        assert second.pts == 4_500
        assert first.time_base == Fraction(1, 90_000)

    asyncio.run(exercise())


def test_static_image_track_exposes_direct_pixels_without_av_conversion(tmp_path):
    image_path = tmp_path / "source.jpg"
    Image.new("RGB", (64, 36), color=(20, 40, 60)).save(image_path)

    async def exercise():
        track = main.StaticImageTrack(str(image_path))
        pixels, pts, time_base = await track.recv_pixels()

        assert pixels.shape == (36, 64, 3)
        assert pts == 0
        assert time_base == Fraction(1, 90_000)

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


def test_signaling_client_ip_prefers_gateway_forwarded_address():
    request = SimpleNamespace(
        headers={"x-real-ip": "100.119.32.60", "x-forwarded-for": "100.119.32.60"},
        client=SimpleNamespace(host="127.0.0.1"),
    )

    assert main.signaling_client_ip(request) == "100.119.32.60"


def test_offer_sdp_omits_unstable_ipv6_candidates():
    sdp = (
        "a=candidate:1 1 udp 123 100.73.64.55 45678 typ host\r\n"
        "a=candidate:2 1 udp 123 fd7a:115c:a1e0::d634:4038 45679 typ host\r\n"
    )

    rewritten = main.prefer_ipv4_candidates(sdp)

    assert "100.73.64.55" in rewritten
    assert "fd7a:115c:a1e0" not in rewritten


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
    monkeypatch.setattr(config, "ENABLE_WEBRTC", True)
    monkeypatch.setattr(config, "TURN_SECRET", "test-shared-secret")
    monkeypatch.setattr(config, "PUBLIC_HOST", "100.73.64.55")
    monkeypatch.setattr(config, "TURN_PORT", 3478)
    monkeypatch.setattr(config, "TURN_TTL_SECONDS", 3600)
    monkeypatch.setattr(config, "TURN_FORCE_RELAY", True)
    monkeypatch.setattr(config, "TURN_TCP_ONLY", True)

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
    assert server["urls"] == ["turn:100.73.64.55:3478?transport=tcp"]


def test_webrtc_signaling_is_disabled_for_jpeg_transport(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_WEBRTC", False)

    try:
        asyncio.run(main.ice_config())
    except HTTPException as error:
        assert error.status_code == 410
        assert "JPEG" in error.detail
    else:
        raise AssertionError("disabled WebRTC signaling should return HTTP 410")


def test_codec_preferences_are_limited_to_vp8():
    async def exercise():
        pc = RTCPeerConnection()
        transceiver = pc.addTransceiver("video", direction="recvonly")

        main.prefer_vp8(pc)

        assert transceiver._preferred_codecs
        assert {codec.mimeType.lower() for codec in transceiver._preferred_codecs} == {"video/vp8"}
        await pc.close()

    asyncio.run(exercise())


def test_bounded_track_returns_an_independent_720_by_480_display_frame(monkeypatch):
    monkeypatch.setattr(config, "DISPLAY_WIDTH", 720)
    monkeypatch.setattr(config, "DISPLAY_HEIGHT", 480)

    class Source:
        async def recv(self):
            return main.VideoFrame.from_ndarray(
                main.np.zeros((1080, 1920, 3), dtype=main.np.uint8),
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
        assert original.width == 1920
        assert original.height == 1080
        assert copied.width == 720
        assert copied.height == 480
        pixels = copied.to_ndarray(format="rgb24")
        assert main.np.all(pixels[:38] == 0)
        assert main.np.all(pixels[-38:] == 0)

    asyncio.run(exercise())


def test_display_downscale_does_not_change_full_quality_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DISPLAY_WIDTH", 720)
    monkeypatch.setattr(config, "DISPLAY_HEIGHT", 480)
    original = main.VideoFrame.from_ndarray(
        main.np.full((1080, 1920, 3), 42, dtype=main.np.uint8),
        format="rgb24",
    )
    original.pts = 90_000
    original.time_base = Fraction(1, 90_000)

    class ExactSource:
        async def recv(self):
            return original

    async def exercise():
        display = await main.BoundedVideoTrack(ExactSource()).recv()
        source_pixels, pts, time_base = main.ProcessedVideoTrack.detach_frame(original)
        output = tmp_path / "camera-1.jpg"
        main.CameraRegistry._save_frame(1, source_pixels, pts, time_base, output)

        assert (display.width, display.height) == (720, 480)
        with Image.open(output) as snapshot:
            assert snapshot.size == (1920, 1080)

    asyncio.run(exercise())


def test_bounded_track_stop_propagates_to_source():
    class Source:
        def __init__(self):
            self.stopped = False

        def stop(self):
            self.stopped = True

    source = Source()
    track = main.BoundedVideoTrack(source)

    track.stop()

    assert source.stopped


def test_delayed_track_releases_frames_at_configured_offset(monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_FPS", 10)

    class Source:
        def __init__(self):
            self.next_pts = 0
            self.stopped = False

        async def recv(self):
            frame = main.VideoFrame.from_ndarray(
                main.np.zeros((24, 32, 3), dtype=main.np.uint8),
                format="rgb24",
            )
            frame.pts = self.next_pts
            self.next_pts += 1
            return frame

        def stop(self):
            self.stopped = True

    async def exercise():
        source = Source()
        delayed = main.DelayedVideoTrack(source, delay_ms=200)

        first = await delayed.recv()
        second = await delayed.recv()

        assert delayed.delay_frames == 2
        assert first.pts == 0
        assert second.pts == 1
        assert source.next_pts == 4
        delayed.stop()
        assert source.stopped

    asyncio.run(exercise())


def test_published_snapshot_includes_verifiable_frame_metadata(tmp_path):
    output = tmp_path / "camera-2.jpg"
    frame = main.VideoFrame.from_ndarray(
        main.np.zeros((24, 32, 3), dtype=main.np.uint8),
        format="rgb24",
    )
    frame.pts = 180_000
    frame.time_base = Fraction(1, 90_000)

    pixels, pts, time_base = main.ProcessedVideoTrack.detach_frame(frame)
    main.CameraRegistry._save_frame(2, pixels, pts, time_base, output)

    metadata = main.json.loads((tmp_path / "camera-2.meta.json").read_text(encoding="utf-8"))
    assert metadata["frameId"].startswith("2-180000-")
    assert metadata["framePts"] == 180_000
    assert metadata["frameTimeBase"] == "1/90000"
    assert metadata["sha256"] == main.hashlib.sha256(output.read_bytes()).hexdigest()
    with Image.open(output) as saved:
        assert saved.size == (32, 24)


def test_ffmpeg_track_uses_probed_source_resolution_without_scale(monkeypatch):
    monkeypatch.setattr(config, "PRESERVE_SOURCE_RESOLUTION", True)
    monkeypatch.setattr(config, "OUTPUT_FPS", 20)
    commands = []

    class Process:
        def __init__(self):
            self.returncode = None

        def terminate(self):
            self.returncode = 0

        def kill(self):
            self.returncode = -9

        async def wait(self):
            return self.returncode

    async def exercise():
        track = main.FfmpegProcessTrack(["-i", "source"], ["source"])

        async def fake_probe():
            return 1920, 1080

        async def fake_exec(*args, **kwargs):
            commands.append(args)
            return Process()

        monkeypatch.setattr(track, "_probe_source_dimensions", fake_probe)
        monkeypatch.setattr(main.asyncio, "create_subprocess_exec", fake_exec)
        await track._start_process()

        assert track.output_width == 1920
        assert track.output_height == 1080
        assert track.frame_size == 1920 * 1080 * 3
        filter_graph = commands[0][commands[0].index("-vf") + 1]
        assert filter_graph == "fps=20"
        assert "scale=" not in filter_graph
        await track._stop_process()

    asyncio.run(exercise())


def test_ffmpeg_process_start_method_survives_aiortc_timestamp_initialization():
    async def exercise():
        track = main.FfmpegProcessTrack([])

        await track.next_timestamp()

        assert isinstance(track._start, float)
        assert callable(track._start_process)
        track.stop()

    asyncio.run(exercise())


def test_ffmpeg_track_refuses_to_downsample_when_probe_fails(monkeypatch):
    monkeypatch.setattr(config, "PRESERVE_SOURCE_RESOLUTION", True)

    async def exercise():
        track = main.FfmpegProcessTrack(["-i", "source"], ["source"])

        async def fake_probe():
            return None

        monkeypatch.setattr(track, "_probe_source_dimensions", fake_probe)
        try:
            await track._start_process()
        except RuntimeError as error:
            assert "拒绝降采样" in str(error)
        else:
            raise AssertionError("原分辨率探测失败时不应启动缩放解码")

    asyncio.run(exercise())


def test_ffmpeg_track_restarts_after_frame_read_timeout(monkeypatch):
    monkeypatch.setattr(config, "FALLBACK_WIDTH", 32)
    monkeypatch.setattr(config, "FALLBACK_HEIGHT", 24)
    monkeypatch.setattr(config, "FRAME_READ_TIMEOUT_SECONDS", 0.01)

    class Reader:
        def __init__(self, should_stall):
            self.should_stall = should_stall

        async def readexactly(self, size):
            if self.should_stall:
                await asyncio.sleep(1)
            return bytes(size)

    class Process:
        def __init__(self, should_stall):
            self.returncode = None
            self.stdout = Reader(should_stall)

        def terminate(self):
            self.returncode = 0

        def kill(self):
            self.returncode = -9

        async def wait(self):
            return self.returncode

    async def exercise():
        track = main.FfmpegProcessTrack([])
        starts = 0

        async def fake_start():
            nonlocal starts
            starts += 1
            track.process = Process(should_stall=starts == 1)

        monkeypatch.setattr(track, "_start_process", fake_start)
        frame = await asyncio.wait_for(track.recv(), timeout=1)

        assert starts == 2
        assert frame.width == 32
        assert frame.height == 24
        track.stop()

    asyncio.run(exercise())
