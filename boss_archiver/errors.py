"""统一异常类型：所有失败路径都必须可观测、可区分（规范 §10、AGENTS Modification Policy）。"""


class UsageError(ValueError):
    """命令行参数 / 配置不合法（面向使用者的错误，附修复提示）。"""


class CollectorError(RuntimeError):
    """采集流程错误（网络、页面结构、未登录等）。"""


class ChallengeError(CollectorError):
    """检测到验证码 / 安全校验等风险信号，立即熔断（SPEC NFR-2）。"""


class LoginError(CollectorError):
    """登录失效或登录超时，需要人工重新扫码。"""
