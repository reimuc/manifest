import pytest

from steam_manifest.core.steam import SteamApp


class FakeClient:
    def __init__(self, mapping=None):
        self.mapping = mapping or {}

    async def get(self, url):
        return self.mapping.get(url)

    async def batch_get(self, urls):
        return {u: self.mapping.get(u) for u in urls}


@pytest.mark.asyncio
async def test_search_app_numeric():
    client = FakeClient()
    steam = SteamApp(client)
    res = await steam.search_app("12345")
    assert res == 12345
    assert steam.app_id == "12345"


@pytest.mark.asyncio
async def test_fetch_app_details_success():
    from steam_manifest.core.constants import Urls

    appid = "42"
    url = Urls.steam_app_details(appid)
    mapping = {url: {appid: {"success": True, "data": {"name": "Game", "dlc": [1, 2]}}}}

    client = FakeClient(mapping)
    steam = SteamApp(client)
    ok = await steam.fetch_app_details(appid)
    assert ok is True
    assert steam.app_name == "Game"
    assert steam.dlc_ids == [1, 2]
