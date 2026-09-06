"""节拍策略（纯逻辑，可单测）：相邻自动化动作的最小间隔 + 随机抖动。

风控护栏设计原则（SPEC NFR-1 / REVIEWS R-2）：
- 低频 + 抖动，避免机械化的固定间隔特征；
- 护栏参数下调必须在 AGENTS.md 的 Requires Human Approval 清单中审批。
"""
from __future__ import annotations

import random
import time
from typing import Callable


class PacingPolicy:
    """两次动作之间至少间隔 min_gap_s 秒，并叠加 [0, jitter_s] 随机抖动。"""

    def __init__(
        self,
        min_gap_s: float,
        jitter_s: float,
        seed: int | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ):
        if min_gap_s < 0 or jitter_s < 0:
            raise ValueError("间隔与抖动不能为负")
        self.min_gap_s = min_gap_s
        self.jitter_s = jitter_s
        self._rng = random.Random(seed)
        self._sleep = sleep_fn if sleep_fn is not None else time.sleep
        self._last_ts: float | None = None

    def compute_delay(self, last_ts: float | None, now: float) -> float:
        """距上次动作 last_ts 时（now 时刻）还需等待的秒数。"""
        if last_ts is None:
            base = 0.0  # 首次动作不强制等待
        else:
            elapsed = max(0.0, now - last_ts)
            base = max(0.0, self.min_gap_s - elapsed)
        return base + self._rng.uniform(0.0, self.jitter_s)

    def wait(self) -> None:
        delay = self.compute_delay(self._last_ts, time.monotonic())
        self._sleep(delay)  # 允许 0 延迟，但保持记录可观测
        self._last_ts = time.monotonic()
