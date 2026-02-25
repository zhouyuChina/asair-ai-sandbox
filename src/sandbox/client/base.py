"""共享 HTTP 客户端基类"""

import asyncio

import httpx

from sandbox.core.exceptions import DifyAPIError
from sandbox.core.logging import get_logger

logger = get_logger(__name__)


class BaseHTTPClient:
    """带重试逻辑的异步 HTTP 客户端基类"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 2,
    ):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        self._max_retries = max_retries

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> dict:
        """带指数退避的请求重试"""
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._client.request(method, path, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                body = e.response.text
                if attempt == self._max_retries or status < 500:
                    raise DifyAPIError(
                        f"HTTP {status}: {body}",
                        status_code=status,
                        response_body=body,
                    ) from e
                wait = 2**attempt
                logger.warning(f"请求失败 (HTTP {status})，{wait}s 后重试 ({attempt + 1}/{self._max_retries})")
                await asyncio.sleep(wait)
            except httpx.RequestError as e:
                if attempt == self._max_retries:
                    raise DifyAPIError(f"请求异常: {e}") from e
                wait = 2**attempt
                logger.warning(f"请求异常: {e}，{wait}s 后重试 ({attempt + 1}/{self._max_retries})")
                await asyncio.sleep(wait)
        raise DifyAPIError("重试次数耗尽")  # pragma: no cover

    async def close(self) -> None:
        await self._client.aclose()
