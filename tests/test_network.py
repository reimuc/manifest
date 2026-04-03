import pytest

from steam_manifest.core.network import HttpClient


class FakeResponse:
    def __init__(self, status=200, json_data=None, read_data=None, headers=None):
        self.status = status
        self._json = json_data
        self._read = read_data or b""
        self.headers = headers or {}

    async def json(self, loads=None):
        return self._json

    async def read(self):
        return self._read

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self, response: FakeResponse):
        self._response = response

    def request(self, method, url, **kwargs):
        # return an object that implements async context manager
        return self._response

    def get(self, url):
        return self._response

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_get_caches_response(monkeypatch):
    # 降低重试参数，避免在异常时测试变慢
    import steam_manifest.core.network as network_mod

    monkeypatch.setattr(network_mod, "RETRY_TIMES", 1)
    monkeypatch.setattr(network_mod, "RETRY_INTERVAL", 0.01)

    # 首次返回JSON，然后缓存应命中
    resp = FakeResponse(status=200, json_data={"key": "value"})
    client = HttpClient()
    client.session = FakeSession(resp)

    # 第一次请求 - 填充缓存
    result1 = await client.get("https://example.com/api")
    assert result1 == {"key": "value"}
    assert "https://example.com/api" in client.cache

    # 第二次请求 - 命中缓存
    result2 = await client.get("https://example.com/api")
    assert result2 == {"key": "value"}
    assert client.cache_hits >= 1


@pytest.mark.asyncio
async def test_raw_get_returns_bytes(monkeypatch):
    resp = FakeResponse(status=200, read_data=b"binarydata")
    client = HttpClient()
    client.session = FakeSession(resp)

    data = await client.raw_get("https://example.com/file.bin")
    assert data == b"binarydata"


@pytest.mark.asyncio
async def test_request_handles_non200(monkeypatch):
    # 非200会导致返回None（在重试后）
    import steam_manifest.core.network as network_mod

    monkeypatch.setattr(network_mod, "RETRY_TIMES", 1)
    monkeypatch.setattr(network_mod, "RETRY_INTERVAL", 0.01)

    resp = FakeResponse(status=500, json_data=None)
    client = HttpClient()
    client.session = FakeSession(resp)

    result = await client.get("https://example.com/error")
    assert result is None
