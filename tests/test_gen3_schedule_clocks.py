"""Keep Gen3 weekly schedule times correct across Vacuula clock versions."""

# ruff: noqa: F811

import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
from test_service_regressions import _call, action_setup  # noqa: F401


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0-b2", "1.1.0-b3", "1.1.0", "1.2.0"])
@pytest.mark.parametrize("now", ["2026-01-19T09:00:00Z", "2026-10-19T09:00:00Z"])
async def test_local_slots_follow_the_server_clock(
    hass, action_setup, freezer, version, now
):  # noqa: F811
    """Keep matching local times on new servers and legacy UTC times on old ones."""
    freezer.move_to(now)
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    coordinator = action_setup[0]
    coordinator.server_info = {"version": version, "timezone": "Asia/Jerusalem"}
    event = {"mode": 1, "day": 1, "startTime": "09:00"}
    await _call(hass, action_setup, "set_schedule", events=[event])
    expected = "09:00"
    if version in {"1.0.0", "1.1.0-b2"}:
        expected = "07:00" if now.startswith("2026-01") else "06:00"
    assert coordinator.command_payloads[-1]["params"]["events"] == [
        {**event, "startTime": expected}
    ]
    assert event["startTime"] == "09:00"


@pytest.mark.parametrize(
    (
        "input_zone",
        "robot_zone",
        "basis",
        "day",
        "time",
        "expected_day",
        "expected_time",
    ),
    [
        ("Asia/Jerusalem", "Asia/Jerusalem", "utc", 6, "23:30", 0, "01:30"),
        ("Asia/Jerusalem", "America/New_York", "local", 0, "00:30", 6, "17:30"),
        ("UTC", "Asia/Kathmandu", "local", 6, "23:30", 0, "05:15"),
        ("Asia/Jerusalem", "America/New_York", "utc", 0, "00:30", 6, "19:30"),
    ],
)
async def test_explicit_timezones_preserve_weekly_instants(  # noqa: F811
    hass,
    action_setup,
    freezer,
    input_zone,
    robot_zone,
    basis,
    day,
    time,
    expected_day,
    expected_time,
):
    """Convert weekly slots across UTC, local zones and fractional offsets."""
    freezer.move_to("2026-01-19T09:00:00Z")
    await hass.config.async_set_time_zone(input_zone)
    coordinator = action_setup[0]
    coordinator.server_info = {"version": "1.1.0", "timezone": robot_zone}
    await _call(
        hass,
        action_setup,
        "set_schedule",
        time_basis=basis,
        events=[{"mode": 2, "day": day, "startTime": time}],
    )
    assert coordinator.command_payloads[-1]["params"]["events"] == [
        {"mode": 2, "day": expected_day, "startTime": expected_time}
    ]


@pytest.mark.parametrize(
    ("basis", "expected_time", "default_zone_lookups"),
    [("local", "17:30", 1), ("utc", "19:30", 0)],
)
async def test_server_timezone_is_awaited_before_writing_schedule(  # noqa: F811
    hass, action_setup, freezer, basis, expected_time, default_zone_lookups
):
    """Load the server zone asynchronously and reuse HA's cached local zone."""
    freezer.move_to("2026-01-19T09:00:00Z")
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    server_timezone = await dt_util.async_get_time_zone("America/New_York")
    coordinator = action_setup[0]
    coordinator.server_info = {"version": "1.1.0", "timezone": "America/New_York"}

    async def load_timezone(timezone_name):
        """Yield control before returning a zone, with no schedule write yet."""
        coordinator.async_command.assert_not_awaited()
        await asyncio.sleep(0)
        return server_timezone

    with (
        patch(
            "custom_components.vacuula_client.services.dt_util.async_get_time_zone",
            new=AsyncMock(side_effect=load_timezone),
        ) as async_lookup,
        patch(
            "custom_components.vacuula_client.services.dt_util.get_time_zone",
            side_effect=AssertionError("Synchronous timezone lookup on the event loop"),
        ),
        patch(
            "custom_components.vacuula_client.services.dt_util.get_default_time_zone",
            wraps=dt_util.get_default_time_zone,
        ) as default_zone,
    ):
        await _call(
            hass,
            action_setup,
            "set_schedule",
            time_basis=basis,
            events=[{"mode": 1, "day": 0, "startTime": "00:30"}],
        )
    async_lookup.assert_awaited_once_with("America/New_York")
    assert default_zone.call_count == default_zone_lookups
    assert coordinator.command_payloads[-1]["params"]["events"] == [
        {"mode": 1, "day": 6, "startTime": expected_time}
    ]


@pytest.mark.parametrize(
    ("server_info", "basis", "clear"),
    [
        ({"version": "1.0.0", "timezone": "Invalid/Timezone"}, "local", False),
        ({"version": "1.0.0", "timezone": "Invalid/Timezone"}, "utc", False),
        ({}, "robot", False),
        ({"version": "1.1.0", "timezone": "Invalid/Timezone"}, "robot", False),
        ({}, "local", True),
        ({"version": "1.1.0", "timezone": "Invalid/Timezone"}, "local", True),
    ],
)
async def test_unneeded_timezones_are_not_loaded(  # noqa: F811
    hass, action_setup, server_info, basis, clear
):
    """Skip server-zone loads for legacy UTC, raw slots and empty schedules."""
    await hass.config.async_set_time_zone("UTC")
    coordinator = action_setup[0]
    coordinator.server_info = server_info
    events = [] if clear else [{"mode": 1, "day": 1, "startTime": "09:00"}]
    with (
        patch(
            "custom_components.vacuula_client.services.dt_util.async_get_time_zone",
            new=AsyncMock(
                side_effect=AssertionError("Unneeded server timezone lookup")
            ),
        ) as async_lookup,
        patch(
            "custom_components.vacuula_client.services.dt_util.get_default_time_zone",
            wraps=dt_util.get_default_time_zone,
        ) as default_zone,
    ):
        await _call(hass, action_setup, "set_schedule", time_basis=basis, events=events)
    async_lookup.assert_not_called()
    assert default_zone.call_count == int(bool(events) and basis == "local")
    assert coordinator.command_payloads[-1]["params"]["events"] == events


@pytest.mark.parametrize(
    ("updated_info", "reject"),
    [
        ({"version": "1.0.0", "timezone": "America/New_York"}, True),
        ({"version": "1.1.0", "timezone": "America/Chicago"}, True),
        ({}, True),
        (
            {"version": "1.1.0", "timezone": "America/New_York", "robots": 2},
            False,
        ),
    ],
)
async def test_clock_metadata_is_rechecked_after_timezone_lookup(  # noqa: F811
    hass, action_setup, freezer, updated_info, reject
):
    """Reject clock changes during lookup while allowing unchanged clock metadata."""
    freezer.move_to("2026-01-19T09:00:00Z")
    server_timezone = await dt_util.async_get_time_zone("America/New_York")
    coordinator = action_setup[0]
    coordinator.server_info = {"version": "1.1.0", "timezone": "America/New_York"}
    events = [{"mode": 1, "day": 0, "startTime": "00:30"}]

    async def replace_server_info(timezone_name):
        """Simulate a metadata poll completing while the zone lookup yields."""
        await asyncio.sleep(0)
        coordinator.server_info = dict(updated_info)
        return server_timezone

    with patch(
        "custom_components.vacuula_client.services.dt_util.async_get_time_zone",
        new=AsyncMock(side_effect=replace_server_info),
    ) as async_lookup:
        if reject:
            with pytest.raises(ServiceValidationError) as error:
                await _call(
                    hass, action_setup, "set_schedule", time_basis="utc", events=events
                )
            assert error.value.translation_key == "schedule_clock_unknown"
            coordinator.async_command.assert_not_awaited()
        else:
            await _call(
                hass, action_setup, "set_schedule", time_basis="utc", events=events
            )
            assert coordinator.command_payloads[-1]["params"]["events"] == [
                {"mode": 1, "day": 6, "startTime": "19:30"}
            ]
    async_lookup.assert_awaited_once_with("America/New_York")


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0"])
async def test_robot_basis_round_trips_raw_schedule_events(hass, action_setup, version):  # noqa: F811
    """Preserve raw times and identified zones without mutating a read response."""
    coordinator = action_setup[0]
    coordinator.server_info = {"version": version, "timezone": "Asia/Jerusalem"}
    event = {
        "mode": 1,
        "day": 6,
        "startTime": "23:30",
        "boundary": {"id": "zone1", "name": "Living room"},
    }
    original = deepcopy(event)
    coordinator.async_command.return_value = {"data": {"events": [event]}}
    response = await _call(hass, action_setup, "get_data", resource="schedule")
    await _call(
        hass,
        action_setup,
        "set_schedule",
        events=response["data"]["events"],
        time_basis="robot",
    )
    assert coordinator.command_payloads[-1]["params"]["events"] == [
        {"mode": 1, "day": 6, "startTime": "23:30", "boundaryId": "zone1"}
    ]
    assert event == original


@pytest.mark.parametrize(
    "server_info",
    [
        {},
        {"version": None},
        {"version": "unknown"},
        {"version": "1.1.0"},
        {"version": "1.1.0", "timezone": "Invalid/Timezone"},
        {"version": "1.1.0", "timezone": 120},
    ],
)
@pytest.mark.parametrize("basis", ["local", "utc"])
async def test_unknown_clock_metadata_rejects_converted_writes(  # noqa: F811
    hass, action_setup, server_info, basis
):
    """Refuse to replace schedules with times in an unverified target clock."""
    coordinator = action_setup[0]
    coordinator.server_info = server_info
    with pytest.raises(ServiceValidationError) as error:
        await _call(
            hass,
            action_setup,
            "set_schedule",
            time_basis=basis,
            events=[{"mode": 1, "day": 1, "startTime": "09:00"}],
        )
    assert error.value.translation_key == "schedule_clock_unknown"
    assert coordinator.command_payloads == []


@pytest.mark.parametrize("clear", [False, True])
async def test_raw_slots_and_clearing_need_no_clock_metadata(hass, action_setup, clear):  # noqa: F811
    """Permit explicit raw slots and empty replacements when metadata is missing."""
    coordinator = action_setup[0]
    coordinator.server_info = {}
    events = [] if clear else [{"mode": 1, "day": 1, "startTime": "09:00"}]
    await _call(
        hass,
        action_setup,
        "set_schedule",
        events=events,
        time_basis="local" if clear else "robot",
    )
    assert coordinator.command_payloads[-1]["params"]["events"] == events
