import pytest

from steam_manifest.core.constants import Steam
from steam_manifest.core.storage import ManifestStorage


@pytest.mark.asyncio
async def test_parse_app_info_ok(monkeypatch):
    # 让 vdf.loads 返回预期结构
    monkeypatch.setattr(
        "steam_manifest.core.storage.vdf.loads",
        lambda s: {"common": {"name": "MyGame"}},
    )

    storage = ManifestStorage()
    name = await storage.parse_app_info(b"irrelevant")
    assert name == "MyGame"


@pytest.mark.asyncio
async def test_parse_depot_key_ok(monkeypatch):
    monkeypatch.setattr(
        "steam_manifest.core.storage.vdf.loads",
        lambda s: {"depots": {"1234": {"DecryptionKey": "abc"}}},
    )

    storage = ManifestStorage()
    ok = await storage.parse_depot_key(b"irrelevant")
    assert ok is True
    assert 1234 in storage.depots and storage.depots[1234] == "abc"


@pytest.mark.asyncio
async def test_save_manifest_file_writes(tmp_path):
    storage = ManifestStorage()
    steam_path = tmp_path

    # 调用并断言写入到 steam_path / DEPOT_CACHE / path
    path = "123456_abcdef.manifest"
    content = b"content"

    ok = await storage.save_manifest_file(path, steam_path, content)
    assert ok is True

    save_path = steam_path / Steam.DEPOT_CACHE / path
    assert save_path.exists()
    # 文件内容应该等于 content
    data = save_path.read_bytes()
    assert data == content
