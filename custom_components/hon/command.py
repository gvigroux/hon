#All credits to https://github.com/Andre0512/pyhOn
from .parameter import HonParameterFixed, HonParameterEnum, HonParameterRange, HonParameterProgram
from homeassistant.exceptions import HomeAssistantError

import logging
_LOGGER = logging.getLogger(__name__)

class HonCommand:
    def __init__(self, name, attributes, connector, device, multi=None, program="", program_name=""):
        self._connector = connector
        self._device = device
        self._name = name
        self._multi = multi or {}
        self._program = program
        self._program_name = program_name
        self._description = attributes.get("description", "")
        self._parameters = self._create_parameters(attributes.get("parameters", {}))
        self._ancillary_parameters = self._create_parameters(attributes.get("ancillaryParameters", {}))

    def __repr__(self):
        return f"{self._name} command"

    def _create_parameters(self, parameters):
        result = {}
        for parameter, attributes in parameters.items():
            match attributes.get("typology"):
                case "range":
                    result[parameter] = HonParameterRange(parameter, attributes)
                case "enum":
                    result[parameter] = HonParameterEnum(parameter, attributes)
                case "fixed":
                    result[parameter] = HonParameterFixed(parameter, attributes)
        if self._multi:
            result["program"] = HonParameterProgram("program", self)
        return result

    @property
    def parameters(self):
        return self._parameters

    @property
    def ancillary_parameters(self):
        return {
            key: parameter.value
            for key, parameter in self._ancillary_parameters.items()
            if not isinstance(parameter, HonParameterProgram)
        }

    async def send(self):
        parameters = {
            name: parameter.value
            for name, parameter in self._parameters.items()
            if not isinstance(parameter, HonParameterProgram)
        }
        if self._name == "startProgram" and self._program:
            # Keep the API's full identifier separate from the UI's short name.
            program_name = self._program_name or (
                f"PROGRAMS.{self._device.appliance_type}.{self._program}"
            )
            program_name = program_name.upper()
            if "prStr" in parameters:
                parameters["prStr"] = program_name
            result = await self._connector.send_command(
                self._device, self._name, parameters, self.ancillary_parameters,
                program_name=program_name,
            )
        else:
            result = await self._connector.send_command(
                self._device, self._name, parameters, self.ancillary_parameters
            )
        if result is False:
            raise HomeAssistantError(
                f"hOn rejected the {self._name} command. Check the integration log."
            )
        if result is True and self._name == "settings":
            self._device.attributes.setdefault("parameters", {}).update(parameters)
        return result

    def get_programs(self):
        return self._multi

    def set_program(self, program):
        self._multi[program]._multi = self._multi
        self._device.commands[self._name] = self._multi[program]
    
    def _get_settings_keys(self, command=None):
        command = command or self
        keys = []
        for key, parameter in command._parameters.items():
            if isinstance(parameter, HonParameterFixed):
                continue
            if key not in keys:
                keys.append(key)
        return keys

    @property
    def setting_keys(self):
        if not self._multi:
            return self._get_settings_keys()
        result = [key for cmd in self._multi.values() for key in self._get_settings_keys(cmd)]
        return list(set(result + ["program"]))

    @property
    def settings(self):
        """Parameters with typology enum and range"""
        if not self._multi:
            return {
                key: parameter
                for key, parameter in self._parameters.items()
                if not isinstance(parameter, HonParameterFixed)
            }

        result = {}
        for key in self.setting_keys:
            parameter = self._parameters.get(key)
            if parameter is None:
                for command in self._multi.values():
                    parameter = command.parameters.get(key)
                    if parameter is not None:
                        break
            if parameter is not None:
                result[key] = parameter
        return result

    def dump(self):
        text = ""
        example = {}
        for key, parameter in self._parameters.items():
            if isinstance(parameter, HonParameterFixed) or key == "program":
                continue
            text += f"""{parameter.dump()}
"""
            example[key] = parameter.default
        return text, repr(example)
