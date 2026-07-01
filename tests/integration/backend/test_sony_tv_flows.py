from unittest.mock import MagicMock, patch

import pytest

from home_cinema_control.devices.tv.adapters.sony import SonyTvController
from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.playback.startup.models import DeviceCommandStatus

pytestmark = pytest.mark.integration


def _response(payload):
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    return response


def _base_config(**overrides):
    tv = {
        "model": "SONY",
        "ip": "10.0.0.5",
        "sony_psk": "psk123",
        "enabled": True,
        "sony_app_uris": {"emby": "com.sony.dtv.tv.emby.embyatv.MainActivity"},
    }
    tv.update(overrides.pop("tv", {}))
    config = {
        "tv": tv,
        "media_servers": {
            "active": "emby",
            "providers": {"emby": {"server_url": "http://emby.local"}},
        },
    }
    config.update(overrides)
    return config


def test_detect_inputs_then_switch_then_confirm_full_chain():
    """Detect HDMI inputs, then switch to one, confirming via a polled
    getPlayingContentInfo that only reports the target uri after two attempts —
    exercises the actual polling loop, not just an immediate match."""
    config = _base_config()
    controller = SonyTvController(config)

    detect_payload = _response({"result": [[
        {"uri": "extInput:hdmi?port=1", "title": "HDMI 1", "connectivity": True},
        {"uri": "extInput:hdmi?port=2", "title": "HDMI 2", "connectivity": True},
    ]]})

    with patch(
        "home_cinema_control.devices.tv.adapters.sony.requests.post",
        return_value=detect_payload,
    ):
        detect_result = controller.retrieve_hdmi_inputs()

    assert detect_result.status == DeviceCommandStatus.SUCCESS
    target = TvInputTarget(input_id=config["tv"]["available_hdmi_inputs"][1]["id"])
    assert target.input_id == "extInput:hdmi?port=2"

    not_yet = _response({"result": [{"uri": "extInput:hdmi?port=1"}]})
    confirmed = _response({"result": [{"uri": "extInput:hdmi?port=2"}]})

    with patch(
        "home_cinema_control.devices.tv.adapters.sony.requests.post",
        side_effect=[not_yet, not_yet, confirmed],
    ):
        switch_result = controller.switch_to_input(target)

    assert switch_result.status == DeviceCommandStatus.SUCCESS


def test_restore_chain_falls_back_to_configured_provider_when_current_app_is_ambiguous():
    """The real restore chain (startup/orchestrator.py -> restoration.py) captures
    get_current_app_id() once at startup and passes it straight to launch_app() at
    finish, with no fallback of its own. This confirms the Sony adapter's own
    fallback closes that gap end-to-end: an ambiguous read at startup still
    produces a launch_app call that succeeds at finish, instead of a silently
    skipped restore."""
    config = _base_config()
    controller = SonyTvController(config)

    with patch(
        "home_cinema_control.devices.tv.adapters.sony.requests.post",
        return_value=_response({"error": [7, "Illegal State"]}),
    ):
        previous_tv_app_id = controller.get_current_app_id()

    assert previous_tv_app_id == "com.sony.dtv.tv.emby.embyatv.MainActivity"

    with patch(
        "home_cinema_control.devices.tv.adapters.sony.requests.post",
        return_value=_response({"result": [{}]}),
    ) as post:
        restore_result = controller.launch_app(previous_tv_app_id)

    assert restore_result.status == DeviceCommandStatus.SUCCESS
    assert post.call_args.kwargs["json"]["params"] == [{"uri": previous_tv_app_id}]


def test_restore_chain_skips_when_already_on_hdmi_input():
    config = _base_config()
    controller = SonyTvController(config)

    with patch(
        "home_cinema_control.devices.tv.adapters.sony.requests.post",
        return_value=_response(
            {"result": [{"uri": "extInput:hdmi?port=2"}]}
        ),
    ):
        previous_tv_app_id = controller.get_current_app_id()

    assert previous_tv_app_id is None

    with patch("home_cinema_control.devices.tv.adapters.sony.requests.post") as post:
        restore_result = controller.launch_app(previous_tv_app_id)

    assert restore_result.status == DeviceCommandStatus.SKIPPED
    post.assert_not_called()


def test_detect_apps_then_media_server_app_id_reflects_persisted_choice():
    config = _base_config(tv={"sony_app_uris": {}})
    controller = SonyTvController(config)

    apps_payload = _response({"result": [[
        {"title": "Emby", "uri": "com.sony.dtv.tv.emby.embyatv.MainActivity"},
        {"title": "YouTube", "uri": "com.sony.dtv.com.google.android.youtube.tv"},
    ]]})

    with patch(
        "home_cinema_control.devices.tv.adapters.sony.requests.post",
        return_value=apps_payload,
    ):
        detect_result = controller.get_application_list()

    assert detect_result.status == DeviceCommandStatus.SUCCESS
    available = config["tv"]["sony_available_apps"]
    assert {"title": "Emby", "uri": "com.sony.dtv.tv.emby.embyatv.MainActivity"} in available

    # Simulate the user picking the Emby entry in Room Setup, persisting it the
    # same way the frontend does before saving the tv config section.
    config["tv"]["sony_app_uris"]["emby"] = "com.sony.dtv.tv.emby.embyatv.MainActivity"

    # A fresh controller instance re-reads the persisted config, same as a new
    # playback session would.
    reloaded_controller = SonyTvController(config)
    assert (
        reloaded_controller.media_server_app_id("emby")
        == "com.sony.dtv.tv.emby.embyatv.MainActivity"
    )
