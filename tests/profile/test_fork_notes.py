import copy

import pytest
from astrbot_plugin_iris_memory.iris_memory.profile.member_notes import MemberNotes
from astrbot_plugin_iris_memory.iris_memory.profile.storage import ProfileStorage
from astrbot_plugin_iris_memory.iris_memory.profile.user_profile import (
    UserProfileManager,
)


class KV:
    def __init__(self):
        self.values = {}

    async def get_kv_data(self, key, default=None):
        return copy.deepcopy(self.values.get(key, default))

    async def put_kv_data(self, key, value):
        self.values[key] = copy.deepcopy(value)

    async def delete_kv_data(self, key):
        self.values.pop(key, None)


def test_markdown_is_human_owned_and_scoped(tmp_path):
    notes = MemberNotes(tmp_path / "notes")
    notes.snapshot("p", "g", "u", {"interests": ["old"]})
    directory = notes.directory("p", "g", "u")
    (directory / "notes.md").write_text("Prefers short replies", encoding="utf-8")
    notes.snapshot("p", "g", "u", {"interests": ["new"]})
    assert notes.read("p", "g", "u") == "Prefers short replies"
    assert '"new"' in (directory / "observations.md").read_text()
    assert notes.read("p", "other-group", "u") == ""
    assert notes.read("other-persona", "g", "u") == ""
    assert notes.directory("../../elsewhere", "g", "u").parent == notes.root
    notes.delete("p", "g", "u")
    assert not directory.exists()


def test_notes_reject_symlink_and_oversized_file(tmp_path):
    notes = MemberNotes(tmp_path / "notes")
    directory = notes.directory("p", "g", "u")
    path = directory / "notes.md"
    target = tmp_path / "outside"
    target.write_text("secret")
    path.symlink_to(target)
    with pytest.raises(ValueError):
        notes.read("p", "g", "u")
    path.unlink()
    path.write_bytes(b"x" * (notes.MAX_BYTES + 1))
    with pytest.raises(ValueError):
        notes.read("p", "g", "u")


@pytest.mark.asyncio
async def test_dashboard_fields_survive_auto_analysis_and_notes_delete(tmp_path):
    storage = ProfileStorage(KV(), notes_dir=tmp_path / "notes")
    storage._is_available = True
    assert await storage.update_user_profile(
        "u", "g", {"interests": ["manual"], "occupation": "author"}
    )
    manager = UserProfileManager(storage)
    await manager.update_from_analysis(
        "u", "g", interests=["automatic"], occupation="invented", confidence=1.0
    )
    profile = await storage.get_user_profile("u", "g")
    assert profile.interests == ["manual"] and profile.occupation == "author"
    assert profile.field_meta["interests"]["source"] == "manual"
    assert await storage.update_user_profile(
        "u", "g", {"interests": ["human correction"]}
    )
    profile = await storage.get_user_profile("u", "g")
    assert profile.interests == ["human correction"]
    directories = list((tmp_path / "notes").iterdir())
    assert len(directories) == 1
    (directories[0] / "notes.md").write_text("Likes astronomy", encoding="utf-8")
    assert await storage.human_notes("u", "g") == "Likes astronomy"
    assert await storage.delete_user_profile("u", "g")
    assert not directories[0].exists()
