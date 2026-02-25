"""令牌桶限流器

用于控制对 Dify API 的请求频率，防止触发限流。
与 asyncio 集成，使用非阻塞等待。
"""

import asyncio
import time


class TokenBucketRateLimiter:
    def __init__(self, rpm: int = 60, burst: int = 10):
        self.rpm = rpm
        self.interval = 60.0 / rpm
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """获取一个令牌，不足时异步等待"""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed / self.interval)
            self.last_refill = now

            if self.tokens >= 1:
                self.tokens -= 1
                return

            wait_time = (1 - self.tokens) * self.interval
            await asyncio.sleep(wait_time)
            self.tokens = 0
            self.last_refill = time.monotonic()
