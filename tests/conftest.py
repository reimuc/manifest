import asyncio
import sys
from contextlib import suppress


def pytest_configure(config):
    # 在 Windows 上使用 SelectorEventLoopPolicy 以兼容某些异步操作
    if sys.platform == "win32":
        with suppress(Exception):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
