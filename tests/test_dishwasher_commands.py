"""Offline command regressions; the Home Assistant runtime is not started.

Run with: python -m unittest discover -s tests -v
HON_FIX_SOURCE optionally selects an unmodified upstream source tree.
Only HA exceptions/coordinator and unrelated constants are stubbed. Parameter,
command and device modules execute unchanged. The service parser and HTTP
payload builder are extracted from their source functions so account setup
and network dependencies are not imported.
"""

import ast
import importlib.util
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
from datetime import datetime
import json
import logging


SOURCE = Path(os.environ.get("HON_FIX_SOURCE", Path(__file__).resolve().parents[1]))
COMPONENT = SOURCE / "custom_components" / "hon"


class HomeAssistantError(Exception):
    """Stand-in for HA's user-visible service error."""


def stub(name, **attributes):
    module = ModuleType(name)
    module.__dict__.update(attributes)
    sys.modules[name] = module
    return module


stub("homeassistant")
stub("homeassistant.exceptions", HomeAssistantError=HomeAssistantError)
stub("homeassistant.helpers")
stub(
    "homeassistant.helpers.update_coordinator",
    DataUpdateCoordinator=object,
    CoordinatorEntity=object,
)
stub("hon_regression", __path__=[str(COMPONENT)])
stub("hon_regression.const", DOMAIN="hon", APPLIANCE_DEFAULT_NAME={})


def load(name):
    spec = importlib.util.spec_from_file_location(
        f"hon_regression.{name}", COMPONENT / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


parameter = load("parameter")
command = load("command")
device_module = load("device")
init_tree = ast.parse((COMPONENT / "__init__.py").read_text(encoding="utf-8"))
parser_node = next(
    node for node in init_tree.body
    if isinstance(node, ast.FunctionDef) and node.name == "get_parameters"
)
parser_namespace = {"ast": ast, "HomeAssistantError": HomeAssistantError}
exec(
    compile(ast.Module(body=[parser_node], type_ignores=[]), str(COMPONENT / "__init__.py"), "exec"),
    parser_namespace,
)
get_parameters = parser_namespace["get_parameters"]

# Execute the real HTTP payload builder against an in-memory HTTP session.
hon_tree = ast.parse((COMPONENT / "hon.py").read_text(encoding="utf-8"))
connection_class = next(
    node for node in hon_tree.body
    if isinstance(node, ast.ClassDef) and node.name == "HonConnection"
)
send_node = next(
    node for node in connection_class.body
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "send_command"
)
send_namespace = {
    "datetime": datetime, "json": json, "_LOGGER": logging.getLogger(__name__),
    "API_URL": "https://api-iot.he.services", "OS": "android", "OS_VERSION": 31,
    "APP_VERSION": "2.27.9", "DEVICE_MODEL": "test",
}
exec(
    compile(ast.Module(body=[send_node], type_ignores=[]), str(COMPONENT / "hon.py"), "exec"),
    send_namespace,
)


class OfflineConnection:
    send_command = send_namespace["send_command"]

    def __init__(self):
        self._mobile_id = "test"
        self._headers = {}
        self._ensure_session = AsyncMock()
        self.response = SimpleNamespace(json=AsyncMock(return_value={"payload": {"resultCode": "0"}}))
        context = AsyncMock()
        context.__aenter__.return_value = self.response
        self._session = SimpleNamespace(post=Mock(return_value=context))


LOG_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/universal_request.json").read_text(encoding="utf-8")
)


def range_parameter(maximum, default=0):
    return {
        "typology": "range", "minimumValue": "0", "maximumValue": str(maximum),
        "incrementValue": "1", "defaultValue": str(default),
    }


def make_device():
    device = object.__new__(device_module.HonDevice)
    device._appliance = {"applianceTypeName": "DW"}
    device._attributes = {"parameters": {
        "waterHard": 7, "lightStatus": 0, "diverterLevel": 0, "prTime": 45,
    }}
    connector = SimpleNamespace(send_command=AsyncMock(return_value=True))
    settings = command.HonCommand("settings", {"parameters": {
        "waterHard": range_parameter(7, 4),
        "lightStatus": range_parameter(1),
    }}, connector, device)
    program = command.HonCommand("startProgram", {"parameters": {
        "waterHard": range_parameter(5, 4),
        "diverterLevel": {"typology": "enum", "enumValues": ["0", "1", "2", "6"], "defaultValue": "0"},
        "prTime": range_parameter(300, 233),
    }}, connector, device, program="eco")
    program._multi = {"eco": program}
    device._commands = {"settings": settings, "startProgram": program}
    return device, connector


class ParametersTest(unittest.TestCase):
    def test_native_yaml_mapping(self):
        data = {"lightStatus": 1, "waterHard": 7}
        self.assertEqual(get_parameters(SimpleNamespace(data={"parameters": data})), data)

    def test_legacy_text_and_json(self):
        for text in ("{'lightStatus': 1}", '{"lightStatus": 1}'):
            with self.subTest(text=text):
                self.assertEqual(get_parameters(SimpleNamespace(data={"parameters": text})), {"lightStatus": 1})

    def test_missing_parameters(self):
        self.assertEqual(get_parameters(SimpleNamespace(data={})), {})

    def test_malformed_requests_from_log(self):
        for text in (
            "{'buzzerDisabled':0,'lastCycleSavingStatus':0,'lightStatus':1,'multiDosingLevelRA':5,'waterHard':7",
            "{lightStatus':1}",
        ):
            with self.subTest(text=text), self.assertRaises(HomeAssistantError):
                get_parameters(SimpleNamespace(data={"parameters": text}))

    def test_wrong_container_or_keys(self):
        for value in ([], "[]", None, 1, {1: "value"}):
            with self.subTest(value=value), self.assertRaises(HomeAssistantError):
                get_parameters(SimpleNamespace(data={"parameters": value}))

    def test_numeric_enum_from_telemetry(self):
        device, _ = make_device()
        setting = device.commands["startProgram"].parameters["diverterLevel"]
        for value in (0, 1, 2, 6, "0", "6"):
            with self.subTest(value=value):
                setting.value = value
                self.assertEqual(setting.value, str(value))
        with self.assertRaises(ValueError):
            setting.value = 3


class CommandsTest(unittest.IsolatedAsyncioTestCase):
    async def test_program_defaults_are_not_overwritten_by_previous_cycle(self):
        device, _ = make_device()
        prepared = device.start_command(program="eco")
        self.assertEqual(prepared.parameters["prTime"].value, 233)
        self.assertEqual(prepared.parameters["waterHard"].value, 4)
        self.assertEqual(device.attributes["parameters"]["waterHard"], 7)

    async def test_preparing_program_keeps_reported_state(self):
        device, _ = make_device()
        before = dict(device.attributes["parameters"])
        device.start_command(parameters={"diverterLevel": 2})
        self.assertEqual(device.attributes["parameters"], before)

    async def test_staged_program_options_survive_other_option_changes(self):
        device, _ = make_device()
        device.start_command(parameters={"prTime": 180})
        prepared = device.start_command(parameters={"diverterLevel": 2})
        self.assertEqual(prepared.parameters["prTime"].value, 180)
        self.assertEqual(prepared.parameters["diverterLevel"].value, "2")

    async def test_start_then_light_preserves_hardness_seven(self):
        device, connector = make_device()
        await device.start_command(program="eco", parameters={"diverterLevel": 2}).send()
        sent_program = connector.send_command.call_args.args[2]
        self.assertEqual(sent_program["diverterLevel"], "2")
        await device.settings_command({"lightStatus": 1}).send()
        connector.send_command.assert_awaited_with(
            device, "settings", {"waterHard": 7, "lightStatus": 1}, {}
        )

    async def test_failed_settings_send_does_not_publish_success(self):
        device, connector = make_device()
        before = dict(device.attributes["parameters"])
        connector.send_command.return_value = False
        with self.assertRaises(HomeAssistantError):
            await device.settings_command({"lightStatus": 1}).send()
        self.assertEqual(device.attributes["parameters"], before)

    async def test_transport_exception_keeps_reported_state(self):
        device, connector = make_device()
        connector.send_command.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            await device.settings_command({"lightStatus": 1}).send()
        self.assertEqual(device.attributes["parameters"]["lightStatus"], 0)

    async def test_successful_settings_remember_change_for_next_command(self):
        device, connector = make_device()
        await device.settings_command({"lightStatus": 1}).send()
        await device.settings_command({"waterHard": 6}).send()
        connector.send_command.assert_awaited_with(
            device, "settings", {"waterHard": 6, "lightStatus": 1}, {}
        )

    async def test_invalid_request_is_not_sent_or_partially_applied(self):
        device, connector = make_device()
        with self.assertRaises(HomeAssistantError):
            await device.settings_command({"lightStatus": 1, "waterHard": 8}).send()
        connector.send_command.assert_not_awaited()
        self.assertEqual(device.commands["settings"].parameters["lightStatus"].value, 0)

    async def test_unknown_parameter_is_reported(self):
        device, connector = make_device()
        with self.assertRaises(HomeAssistantError):
            await device.settings_command({"lightStatu": 1}).send()
        connector.send_command.assert_not_awaited()

    async def test_seven_is_valid_for_settings_but_not_for_program(self):
        device, connector = make_device()
        with self.assertRaises(HomeAssistantError):
            await device.start_command(parameters={"waterHard": 7}).send()
        connector.send_command.assert_not_awaited()
        await device.settings_command({"waterHard": 7}).send()
        self.assertEqual(connector.send_command.call_args.args[2]["waterHard"], 7)

    async def test_other_appliance_keeps_previous_program_sync(self):
        device, _ = make_device()
        device._appliance["applianceTypeName"] = "WM"
        device._attributes["parameters"]["waterHard"] = 3
        prepared = device.start_command()
        self.assertEqual(prepared.parameters["prTime"].value, 45)
        self.assertEqual(prepared.parameters["waterHard"].value, 3)

    async def test_examples_quote_text_and_allow_empty_commands(self):
        device, connector = make_device()
        for attributes, expected in (
            ({}, {}),
            ({"parameters": {"mode": {"typology": "enum", "enumValues": ["auto"], "defaultValue": "auto"}}}, {"mode": "auto"}),
        ):
            with self.subTest(attributes=attributes):
                _, example = command.HonCommand("settings", attributes, connector, device).dump()
                parsed = get_parameters(SimpleNamespace(data={"parameters": example}))
                self.assertEqual(parsed, expected)


class ProgramPayloadTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.connection = OfflineConnection()
        self.device, _ = make_device()
        self.device._appliance["macAddress"] = "00-00-00-00-00-00"
        self.device._hon = self.connection
        attributes = {
            group: {
                key: {"typology": "fixed", "fixedValue": value}
                for key, value in LOG_FIXTURE[group].items() if key != "program"
            }
            for group in ("parameters", "ancillaryParameters")
        }
        parameters = attributes["parameters"]
        parameters["diverterLevel"] = {
            "typology": "enum", "enumValues": [0, 1, 2, 6], "defaultValue": "0"
        }
        for key in ("halfLoad", "extraDry", "openDoor", "hygiene", "tabStatus"):
            parameters[key] = range_parameter(1)
        parameters["waterHard"] = range_parameter(7, 4)
        # Load multiple programs through the real loader, as in the device.
        self.connection.load_commands = AsyncMock(return_value={
            "applianceModel": {"options": LOG_FIXTURE["applianceOptions"]},
            "options": {}, "dictionaryId": "test",
            "startProgram": {
                "PROGRAMS.DW.FIRST": attributes,
                "PROGRAMS.DW.IOT_VOICE_UNIVERSAL": attributes,
            },
        })
        await self.device.load_commands()

    async def test_selected_program_is_serialized_like_pyhon(self):
        prepared = self.device.start_command("iot_voice_universal", {
            "diverterLevel": "0", "halfLoad": "0", "extraDry": "1",
            "openDoor": "1", "hygiene": "1", "tabStatus": "1", "waterHard": "7",
        })
        await prepared.send()
        payload = self.connection._session.post.call_args.kwargs["json"]
        self.assertEqual(payload["programName"], "PROGRAMS.DW.IOT_VOICE_UNIVERSAL")
        expected_parameters = dict(LOG_FIXTURE["parameters"])
        expected_parameters.pop("program")
        expected_parameters["prStr"] = "PROGRAMS.DW.IOT_VOICE_UNIVERSAL"
        self.assertEqual(payload["parameters"], expected_parameters)
        expected_ancillary = dict(LOG_FIXTURE["ancillaryParameters"])
        expected_ancillary.pop("program")
        self.assertEqual(payload["ancillaryParameters"], expected_ancillary)
        self.assertEqual(prepared.parameters["prStr"].value, "0")

    async def test_first_program_also_has_full_name(self):
        await self.device.start_command("first").send()
        payload = self.connection._session.post.call_args.kwargs["json"]
        self.assertEqual(payload["programName"], "PROGRAMS.DW.FIRST")
        self.assertEqual(payload["parameters"]["prStr"], "PROGRAMS.DW.FIRST")

    async def test_settings_keep_their_existing_payload(self):
        parameters = {"lightStatus": 1, "waterHard": 7}
        await self.connection.send_command(self.device, "settings", parameters, {})
        payload = self.connection._session.post.call_args.kwargs["json"]
        self.assertNotIn("programName", payload)
        self.assertEqual(payload["parameters"], parameters)

    async def test_washer_program_preserves_full_api_identifier(self):
        for appliance_type in ("WM", "WD"):
            with self.subTest(appliance_type=appliance_type):
                self.device._appliance["applianceTypeName"] = appliance_type
                prepared = command.HonCommand(
                    "startProgram", {"parameters": {
                        "prStr": {"typology": "fixed", "fixedValue": "0"},
                    }}, self.connection, self.device,
                    program="cotton", program_name="PROGRAMS.WM_WD.COTTON",
                )
                await prepared.send()
                payload = self.connection._session.post.call_args.kwargs["json"]
                self.assertEqual(payload["programName"], "PROGRAMS.WM_WD.COTTON")
                self.assertEqual(payload["parameters"]["prStr"], payload["programName"])
                self.assertNotIn("program", payload["parameters"])
                self.assertNotIn("program", payload["ancillaryParameters"])

    async def test_legacy_washer_send_keeps_upstream_program_name_fallback(self):
        for appliance_type in ("WM", "WD"):
            for parameters, ancillary in (
                ({"program": "cotton"}, {}),
                ({}, {"program": "cotton"}),
            ):
                with self.subTest(appliance_type=appliance_type, parameters=parameters):
                    self.device._appliance["applianceTypeName"] = appliance_type
                    await self.connection.send_command(
                        self.device, "startProgram", parameters, ancillary
                    )
                    payload = self.connection._session.post.call_args.kwargs["json"]
                    self.assertEqual(payload["programName"], "PROGRAMS.WM_WD.COTTON")

    async def test_program_without_prstr_does_not_gain_that_parameter(self):
        prepared = self.device.start_command("iot_voice_universal")
        prepared.parameters.pop("prStr")
        await prepared.send()
        payload = self.connection._session.post.call_args.kwargs["json"]
        self.assertNotIn("prStr", payload["parameters"])
        self.assertEqual(payload["programName"], "PROGRAMS.DW.IOT_VOICE_UNIVERSAL")

    async def test_api_rejection_is_reported_at_command_level(self):
        self.connection.response.json.return_value = {"payload": {"resultCode": "1"}}
        with self.assertRaises(HomeAssistantError):
            await self.device.start_command("iot_voice_universal").send()


if __name__ == "__main__":
    unittest.main()
