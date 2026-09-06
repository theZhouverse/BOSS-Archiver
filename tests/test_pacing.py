"""节拍策略与风险识别测试。"""
import pytest

from boss_archiver.pacing import PacingPolicy
from boss_archiver.risk import (
    STATE_CHALLENGE,
    STATE_LOGIN,
    STATE_OK,
    classify_page,
)


def test_policy_rejects_negative():
    with pytest.raises(ValueError):
        PacingPolicy(-1, 1)
    with pytest.raises(ValueError):
        PacingPolicy(1, -1)


def test_first_call_no_minimum():
    policy = PacingPolicy(min_gap_s=2.5, jitter_s=1.0, seed=7)
    delay = policy.compute_delay(None, now=100.0)
    assert 0.0 <= delay <= 1.0  # 首次只含抖动


def test_subsequent_delay_within_bounds():
    policy = PacingPolicy(min_gap_s=2.5, jitter_s=1.0, seed=7)
    for _ in range(50):
        delay = policy.compute_delay(last_ts=100.0, now=101.0)  # 距上次仅 1s
        # 只需补齐剩余间隔（min_gap - elapsed）并叠加抖动 => 两次动作至少隔 min_gap
        assert 1.5 <= delay <= 2.5


def test_elapsed_beyond_gap_only_jitter():
    policy = PacingPolicy(min_gap_s=2.5, jitter_s=0.5, seed=7)
    delay = policy.compute_delay(last_ts=100.0, now=200.0)  # 间隔早已足够
    assert 0.0 <= delay <= 0.5


def test_seed_deterministic():
    p1 = PacingPolicy(2.0, 1.0, seed=42)
    p2 = PacingPolicy(2.0, 1.0, seed=42)
    assert [p1.compute_delay(None, 0) for _ in range(3)] == [
        p2.compute_delay(None, 0) for _ in range(3)
    ]


def test_wait_sleeps_and_tracks():
    sleeps: list[float] = []
    policy = PacingPolicy(min_gap_s=2.0, jitter_s=0.0, seed=1, sleep_fn=sleeps.append)
    policy.wait()  # 首次：只睡抖动 0
    assert sleeps[-1] >= 0
    policy.wait()  # 距上次 <2s：至少补足 2s
    assert sleeps[-1] >= 2.0


def test_risk_classify():
    assert classify_page("https://www.zhipin.com/web/geek/job?city=101210100", "Boss直聘") == STATE_OK
    assert classify_page("https://verify.zhipin.com/captcha") == STATE_CHALLENGE
    assert classify_page("https://www.zhipin.com/job_detail/abc.html", "安全验证") == STATE_CHALLENGE
    assert classify_page("https://www.zhipin.com/web/user/?ka=header-login") == STATE_LOGIN
    assert classify_page("https://passport.zhipin.com/login") == STATE_LOGIN
