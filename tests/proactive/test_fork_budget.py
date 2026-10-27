from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from astrbot_plugin_iris_memory.iris_memory.proactive.config import ConfigManager
from astrbot_plugin_iris_memory.iris_memory.proactive.parser import Decision
from astrbot_plugin_iris_memory.iris_memory.proactive.participation_budget import (
    ParticipationBudget,
)


def test_budget_cooldown_rolling_limit_and_restart():
    budget = ParticipationBudget()
    for now in (100, 200, 300):
        assert budget.check("g", now=now) == "allowed"
        budget.reserve("g", now=now)
    restored = ParticipationBudget()
    restored.load(budget.entries)
    assert restored.check("g", now=350) == "cooldown"
    assert restored.check("g", now=400) == "rolling_limit"
    assert restored.check("g", now=1201) == "allowed"
    assert restored.check("other-group", now=350) == "allowed"


@pytest.mark.asyncio
async def test_dry_run_evaluates_without_reserving_or_speaking():
    from astrbot_plugin_iris_memory.main import IrisMemoryPlugin

    plugin = object.__new__(IrisMemoryPlugin)
    plugin._triggering = {"g": 1}
    plugin._reply_config = ConfigManager(
        {"proactive": {"group_whitelist": ["bot:GroupMessage:g"]}}
    )
    plugin._participation_budget = ParticipationBudget()
    plugin._decision_core = SimpleNamespace(
        decide=AsyncMock(
            return_value=SimpleNamespace(
                error="",
                decision=Decision(action="speak"),
                raw_text="{}",
                system_prompt="",
                user_prompt="",
                duration_ms=1,
            )
        )
    )
    plugin._llm_manager = object()
    plugin._stats = Mock()
    plugin._release_decision_ticket = Mock()
    plugin.context = SimpleNamespace(
        persona_manager=SimpleNamespace(
            get_default_persona_v3=AsyncMock(
                return_value={"prompt": "A curious detective"}
            )
        )
    )
    event = Mock()
    event.get_group_id.return_value = "g"
    event.unified_msg_origin = "bot:GroupMessage:g"
    event.get_extra.return_value = {"motive": "chime_in", "provider_id": "judge"}
    assert await plugin._handle_reply_decision(event) is True
    event.stop_event.assert_called_once()
    assert not plugin._participation_budget.entries
    request = plugin._decision_core.decide.call_args.args[0]
    assert request.persona_prompt == "A curious detective"


@pytest.mark.asyncio
async def test_no_whitelisted_group_never_calls_judge():
    from astrbot_plugin_iris_memory.main import IrisMemoryPlugin

    plugin = object.__new__(IrisMemoryPlugin)
    plugin._triggering = {"g": 1}
    plugin._reply_config = ConfigManager({})
    plugin._participation_budget = ParticipationBudget()
    plugin._decision_core = SimpleNamespace(decide=AsyncMock())
    plugin._release_decision_ticket = Mock()
    event = Mock()
    event.get_group_id.return_value = "g"
    event.unified_msg_origin = "bot:GroupMessage:g"
    event.get_extra.return_value = {"motive": "chime_in"}
    assert await plugin._handle_reply_decision(event) is True
    plugin._decision_core.decide.assert_not_awaited()


def test_cooldown_longer_than_window_is_still_enforced():
    budget = ParticipationBudget()
    budget.reserve("g", now=100)
    assert budget.check("g", now=200, cooldown=300, window=60) == "cooldown"
    assert budget.check("g", now=401, cooldown=300, window=60) == "allowed"


@pytest.mark.asyncio
async def test_live_decision_reserves_before_main_pipeline_without_provider_override():
    import asyncio

    from astrbot_plugin_iris_memory.main import IrisMemoryPlugin

    plugin = object.__new__(IrisMemoryPlugin)
    plugin._triggering = {"g": 1}
    plugin._reply_config = ConfigManager(
        {"proactive": {"dry_run": False, "group_whitelist": ["bot:GroupMessage:g"]}}
    )
    plugin._participation_budget = ParticipationBudget()
    plugin._decision_core = SimpleNamespace(
        decide=AsyncMock(
            return_value=SimpleNamespace(
                error="",
                decision=Decision(action="speak"),
                raw_text="{}",
                system_prompt="",
                user_prompt="",
                duration_ms=1,
            )
        )
    )
    plugin._llm_manager = object()
    plugin._stats = Mock()
    plugin._release_decision_ticket = Mock()
    plugin._state = SimpleNamespace(get_lock=lambda group: asyncio.Lock())
    plugin._passive_active = {}
    plugin._reply_in_progress = {}
    plugin._kv_save = AsyncMock()
    plugin.context = SimpleNamespace(
        persona_manager=SimpleNamespace(
            get_default_persona_v3=AsyncMock(return_value={"prompt": "A detective"})
        )
    )
    event = Mock()
    event.get_group_id.return_value = "g"
    event.unified_msg_origin = "bot:GroupMessage:g"
    event.get_extra.return_value = {
        "motive": "chime_in",
        "provider_id": "text-only-judge",
    }
    assert await plugin._handle_reply_decision(event) is False
    event.stop_event.assert_not_called()
    assert len(plugin._participation_budget.entries["g"]) == 1
    plugin._kv_save.assert_awaited_once()
    assert all(
        call.args[0] not in {"selected_provider", "iris_llm_provider_id"}
        for call in event.set_extra.call_args_list
    )
