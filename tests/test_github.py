import pytest

from steam_manifest.core.github import GitHubRepo
from steam_manifest.core.storage import ManifestStorage


class SimpleFakeClient:
    def __init__(self, mapping=None):
        self.mapping = mapping or {}

    async def get(self, url):
        return self.mapping.get(url)

    async def raw_get(self, url):
        # Return bytes for raw_get
        return b"content"


@pytest.mark.asyncio
async def test_check_rate_limit_remaining_zero():
    from steam_manifest.core.constants import Urls

    mapping = {Urls.GITHUB_RATE_LIMIT: {"rate": {"remaining": 0, "reset": 12345}}}
    client = SimpleFakeClient(mapping)
    storage = ManifestStorage()
    repo = GitHubRepo(client, storage)

    ok = await repo.check_rate_limit()
    assert ok is False
    assert "reset_time" in repo.rate_limit_info


@pytest.mark.asyncio
async def test_find_repository_picks_latest(monkeypatch):
    # 模拟两个仓库，第二个返回较新的日期
    async def fake_get(url):
        if "repo1" in url:
            return {
                "commit": {"commit": {"committer": {"date": "2020-01-01T00:00:00Z"}}}
            }
        if "repo2" in url:
            return {
                "commit": {"commit": {"committer": {"date": "2022-01-01T00:00:00Z"}}}
            }
        return None

    class Client:
        async def get(self, url):
            return await fake_get(url)

    storage = ManifestStorage()
    client = Client()
    gh = GitHubRepo(client, storage)

    chosen = await gh.find_repository("123", custom_repos=["repo1", "repo2"])
    assert chosen == "repo2"


@pytest.mark.asyncio
async def test_process_files_calls_storage(monkeypatch, tmp_path):
    # patch Progress to avoid rich output in tests
    import steam_manifest.core.github as github_mod

    class DummyProgress:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def add_task(self, *a, **k):
            return 1

        def advance(self, *a, **k):
            pass

    monkeypatch.setattr(github_mod, "Progress", DummyProgress)

    # Fake client that returns branch/tree and file contents
    class Client:
        async def get(self, url):
            # branch info
            if "branches" in url:
                return {"commit": {"commit": {"tree": {"url": "tree_url"}}}}
            if url == "tree_url":
                return {
                    "tree": [
                        {"path": "a.manifest", "type": "blob"},
                        {"path": "appinfo.vdf", "type": "blob"},
                        {"path": "key.vdf", "type": "blob"},
                        {"path": "config.json", "type": "blob"},
                    ]
                }
            if url.endswith("config.json"):
                return {"dlcs": [111], "packagedlcs": []}
            return None

        async def raw_get(self, url):
            return b"dummy"

    storage = ManifestStorage()

    # Provide storage methods to be called
    async def fake_save_manifest(path, steam_path, content):
        return True

    async def fake_parse_appinfo(content):
        return "Name"

    async def fake_parse_depot_key(content):
        return True

    async def fake_parse_config(config):
        return [111], []

    storage.save_manifest_file = fake_save_manifest
    storage.parse_app_info = fake_parse_appinfo
    storage.parse_depot_key = fake_parse_depot_key
    storage.parse_config_json = fake_parse_config

    client = Client()
    gh = GitHubRepo(client, storage)

    files = [
        {"path": "a.manifest", "type": "blob"},
        {"path": "appinfo.vdf", "type": "blob"},
        {"path": "key.vdf", "type": "blob"},
        {"path": "config.json", "type": "blob"},
    ]

    ok = await gh.process_files("repo", "branch", files, tmp_path)
    assert ok is True
