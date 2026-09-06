"""命令行入口：解析参数 → Settings 校验 → Collector → CSV 写出。"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .collector import Collector
from .config import CITY_CODES, Settings
from .errors import ChallengeError, CollectorError, LoginError, UsageError
from .writer import default_output_path, write_csv

DEFAULT_PAGES = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="boss-archiver",
        description="BOSS 直聘职位检索与本地归档工具（个人求职辅助，请低频使用）",
    )
    parser.add_argument("--city", default="杭州",
                        help="城市名（杭州/杭州市）或城市 code（101210100）；--list-cities 查看内置城市")
    parser.add_argument("--query", "-q", default="", help="职位关键词，如 Java开发")
    parser.add_argument("--pages", "-p", type=int, default=DEFAULT_PAGES,
                        help=f"抓取页数（1~8，默认 {DEFAULT_PAGES}）")
    parser.add_argument("--no-detail", action="store_true", help="跳过职位描述抓取，只导列表")
    parser.add_argument("--no-refine", action="store_true", help="跳过人工微调筛选的暂停，全自动执行")
    parser.add_argument("--out", type=Path, default=None,
                        help="输出文件路径（默认 out/boss直聘_城市_关键词_时间戳.csv）")
    parser.add_argument("--profile", type=Path, default=None,
                        help="浏览器用户数据目录（默认 .runtime/browser_profile，登录态复用）")
    parser.add_argument("--login-timeout", type=float, default=180.0, help="扫码登录最长等待秒数（默认 180）")
    parser.add_argument("--headless", action="store_true", help="无头模式（调试用）")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出 DEBUG 日志")
    parser.add_argument("--list-cities", action="store_true", help="列出内置城市码表后退出")
    parser.add_argument("--version", action="version", version=f"boss-archiver {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_cities:
        for name in sorted(CITY_CODES):
            print(f"{name}	{CITY_CODES[name]}")
        return 0

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        settings = Settings(
            city=args.city,
            query=args.query,
            pages=args.pages,
            fetch_details=not args.no_detail,
            refine_filters=not args.no_refine,
            profile_dir=args.profile if args.profile is not None else Path(".runtime") / "browser_profile",
            output_path=args.out,
            headless=args.headless,
            verbose=args.verbose,
            login_timeout_s=args.login_timeout,
        )
        settings.validate()
    except UsageError as exc:
        parser.error(str(exc))  # argparse 退出码 2

    try:
        result = Collector(settings).run()
    except ChallengeError as exc:
        print(f"[已熔断] {exc}", file=sys.stderr)
        return 4
    except LoginError as exc:
        print(f"[登录] {exc}", file=sys.stderr)
        return 3
    except CollectorError as exc:
        print(f"[采集失败] {exc}", file=sys.stderr)
        return 3
    except Exception:
        logging.getLogger("boss_archiver").exception("未预期错误")
        return 1

    path = settings.output_path or default_output_path(settings.out_dir, settings.city, settings.query)
    rows = write_csv(result.jobs, path)
    print("=" * 62)
    print(f"检索条件：城市={settings.city}（code {settings.city_code()}） "
          f"关键词={settings.query or '（不限）'} 目标页数={settings.pages}")
    print(f"实际抓取 {result.pages_fetched} 页；去重后职位 {rows} 条；详情抓取失败 {result.detail_failures} 条")
    print(f"输出文件：{path.resolve()}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
