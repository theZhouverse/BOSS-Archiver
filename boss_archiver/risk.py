"""风险信号识别（纯函数，可单测）。

检测到验证码/安全校验/登录失效等信号时，调用方必须熔断退出（SPEC NFR-2），
本项目不做任何自动绕过（AGENTS.md Forbidden）。
"""
from __future__ import annotations

# URL 中出现即视为安全校验的信号
CHALLENGE_URL_MARKERS = (
    "captcha",
    "verify",
    "geetest",
    "risk-control",
    "riskcontrol",
    "security-check",
    "securitycheck",
    "waf",
)
# 标题中出现即视为安全校验的信号
CHALLENGE_TITLE_MARKERS = ("安全验证", "验证中心", "人机验证", "访问验证", "异常访问")
# URL 中出现即视为登录失效/未登录
LOGIN_URL_MARKERS = ("/web/user/", "passport.zhipin.com", "/login")

STATE_OK = "ok"
STATE_CHALLENGE = "challenge"
STATE_LOGIN = "login"

STATE_DESCRIPTION = {
    STATE_OK: "页面状态正常",
    STATE_CHALLENGE: "检测到验证码/安全校验（已熔断，请稍后再试并降低 --pages）",
    STATE_LOGIN: "登录失效（请重新运行并扫码登录）",
}


def classify_page(url: str, title: str = "") -> str:
    """把页面 URL/标题归类为 ok / challenge / login 之一。"""
    low_url = (url or "").lower()
    low_title = (title or "").lower()
    for marker in CHALLENGE_URL_MARKERS:
        if marker in low_url:
            return STATE_CHALLENGE
    for marker in CHALLENGE_TITLE_MARKERS:
        if marker in low_title:
            return STATE_CHALLENGE
    for marker in LOGIN_URL_MARKERS:
        if marker in low_url:
            return STATE_LOGIN
    return STATE_OK


def describe(state: str) -> str:
    return STATE_DESCRIPTION.get(state, state)
