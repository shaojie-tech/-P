"""语音 barge-in 竞态回归测试（离线，mock LLM/TTS）。

覆盖三个真实事故路径：
1. 打断后旧回复任务的迟到帧泄入新回复（两种声音混播 / 打断后不出声的根因）；
2. 取消后 LLM 生成器未关闭，底层流继续拉取烧 token；
3. 开场白异常被吞，前端永远收不到终态帧（卡在"正在接通"）。
"""

import asyncio
import json
import threading
import time
import unittest
from contextlib import suppress
from unittest import mock

from app.services.tts import TtsUnit
from app.voice_ws import VoiceConnection, _GuardedSender, _produce, _produce_greeting


class FakeWS:
    """记录所有已发送帧的假 WebSocket。"""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_text(self, data: str) -> None:
        self.sent.append(json.loads(data))


class FakeSession:
    """假会话：handle_stream 返回测试控制的生成器。"""

    def __init__(self, stream_factory) -> None:
        self.display_history: list = []
        self.messages: list = []
        self._stream_factory = stream_factory

    def handle_stream(self, text: str):
        return self._stream_factory(text)


async def _fake_synth(state, sentence):
    return TtsUnit(text=sentence, blocks=[b"FAKE-AUDIO"], ok=True)


async def _wait_for(pred, timeout: float = 3.0) -> bool:
    """轮询等待条件成立（测试内定时同步用）。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        await asyncio.sleep(0.01)
    return False


class VoiceRaceTests(unittest.TestCase):
    def test_stale_task_frames_never_leak_into_new_reply(self):
        """旧回复卡在不可中断的 LLM 线程时开始新回复：旧任务的帧一帧都不能泄入。"""
        asyncio.run(self._stale_frames_case())

    async def _stale_frames_case(self):
        ws = FakeWS()
        conn = VoiceConnection(ws, {"id": 1})
        gate = threading.Event()
        entered = threading.Event()  # 生成器已进入阻塞段（任务必然卡在 to_thread 上）

        def slow_stream(text):
            # 首块足够长（>TTS_FIRST_CHARS）触发音频推送，然后卡在线程里
            yield "旧回复第一段内容。" * 8
            entered.set()
            gate.wait(5)
            yield "旧回复第二段内容。"

        def fast_stream(text):
            yield "新回复内容。"

        old_session = FakeSession(slow_stream)
        new_session = FakeSession(fast_stream)

        with (
            mock.patch("app.voice_ws.CANCEL_GRACE_SECONDS", 0.2),
            mock.patch("app.services.tts.synth", side_effect=_fake_synth),
        ):
            conn.generation = old = asyncio.create_task(
                _produce(_GuardedSender(conn, conn.epoch), old_session, "旧问题", conn.tts_state)
            )
            # 等旧回复真正推出音频帧并进入不可中断的线程阻塞
            self.assertTrue(
                await _wait_for(
                    lambda: entered.is_set() and any(m["type"] == "audio_end" for m in ws.sent)
                )
            )
            # barge-in：取消旧任务 → epoch 前进 → 开始新回复。
            # 旧任务的 cancel 立即送达，但其 LLM 拉流线程成为孤儿继续阻塞——
            # 这正是迟到帧泄漏的事故窗口，守卫必须兜住。
            await conn._cancel_generation()
            self.assertTrue(old.done(), "cancel 应立即送达旧任务（孤儿线程除外）")
            conn.epoch += 1
            boundary = len(ws.sent)
            new_task = asyncio.create_task(
                _produce(_GuardedSender(conn, conn.epoch), new_session, "新问题", conn.tts_state)
            )
            await asyncio.wait_for(new_task, timeout=5)

            # 新回复的所有音频 sid 必须 >= 自己的 first_sid（全局单调，绝不与旧回复重叠）
            new_frames = ws.sent[boundary:]
            first_sid = next(m["first_sid"] for m in new_frames if m["type"] == "reply_start")
            self.assertTrue(any(m["type"] == "done" for m in new_frames))
            for m in new_frames:
                if m["type"] in ("audio_start", "audio", "audio_end", "tts_error"):
                    self.assertGreaterEqual(m["sid"], first_sid)
                self.assertNotEqual(m.get("content"), "旧回复第二段内容。")

            # 放开孤儿线程：它拉出的下一块必须被静默丢弃，一帧都不能再上 WebSocket
            n_before = len(ws.sent)
            gate.set()
            await asyncio.sleep(0.5)
            self.assertEqual(len(ws.sent), n_before, "被打断的旧回复不得再向 WebSocket 推帧")

            # 跨回复 sid 全局唯一：新旧音频永不会被前端拼进同一缓冲
            sids = [m["sid"] for m in ws.sent if m["type"] == "audio_end"]
            self.assertTrue(sids)
            self.assertEqual(len(set(sids)), len(sids), "音频 sid 必须全局唯一")

    def test_llm_stream_closed_after_cancel(self):
        """取消回复后必须关闭 LLM 生成器，阻断底层流继续产 token。"""
        asyncio.run(self._stream_closed_case())

    async def _stream_closed_case(self):
        ws = FakeWS()
        conn = VoiceConnection(ws, {"id": 1})
        tracker = {"closed": False}

        def stream(text):
            try:
                yield "第一段。"
                yield "第二段。"
                yield "第三段。"
            finally:
                tracker["closed"] = True

        session = FakeSession(stream)
        with mock.patch("app.services.tts.synth", side_effect=_fake_synth):
            task = asyncio.create_task(
                _produce(_GuardedSender(conn, conn.epoch), session, "问题", conn.tts_state)
            )
            self.assertTrue(await _wait_for(lambda: any(m["type"] == "delta" for m in ws.sent)))
            task.cancel()
            with suppress(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=5)
        self.assertTrue(tracker["closed"], "取消后必须关闭 LLM 生成器（否则继续烧 token）")

    def test_greeting_failure_sends_error_frame(self):
        """开场白合成异常：必须发 error 终态帧，不能静默死亡让前端卡在'正在接通'。"""
        asyncio.run(self._greeting_error_case())

    async def _greeting_error_case(self):
        ws = FakeWS()
        conn = VoiceConnection(ws, {"id": 1})
        with mock.patch("app.services.tts.synth", side_effect=RuntimeError("boom")):
            await _produce_greeting(
                _GuardedSender(conn, conn.epoch), conn.tts_state, "你好，我是面试官小P。"
            )
        types = [m["type"] for m in ws.sent]
        self.assertIn("reply_start", types)
        self.assertIn("error", types, "开场白失败必须发 error 帧兜底")
        self.assertEqual(ws.sent[-1]["code"], "internal")


if __name__ == "__main__":
    unittest.main()
