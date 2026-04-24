import logging

from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,CoordinatorEntity)

from .const import DOMAIN, APPLIANCE_DEFAULT_NAME
from .command import HonCommand
from .parameter import HonParameterFixed, HonParameterEnum

_LOGGER = logging.getLogger(__name__)

class HonDevice(CoordinatorEntity):
    def __init__(self, hon, coordinator, appliance) -> None:
        super().__init__(coordinator)

        self._hon           = hon
        self._coordinator   = coordinator
        self._appliance     = appliance
        self._brand         = appliance["brand"]
        self._type_name     = appliance["applianceTypeName"]
        self._type_id       = appliance["applianceTypeId"]
        self._name          = appliance.get("nickName", APPLIANCE_DEFAULT_NAME.get(str(self._type_id), "Device ID: " + str(self._type_id)))
        self._mac           = appliance["macAddress"]
        self._model         = appliance["modelName"]
        self._series        = appliance.get("series", "")
        self._model_id      = appliance["applianceModelId"]
        self._serial_number = appliance["serialNumber"]
        self._fw_version    = appliance["fwVersion"]

        self._commands              = {}
        self._appliance_model       = {}
        self._attributes            = {}
        self._statistics            = {}


    def __getitem__(self, item):
        if "." in item:
            result = self.data
            for key in item.split("."):
                if all([k in "0123456789" for k in key]) and type(result) is list:
                    result = result[int(key)]
                else:
                    result = result[key]
            return result
        else:
            if item in self.data:
                return self.data[item]
            if item in self.attributes["parameters"]:
                return self.attributes["parameters"].get(item)
            return self.appliance[item]

    def set(self, item, value):
        if item in self.data:
            self.data[item] = value
        elif item in self.attributes["parameters"]:
            self.attributes["parameters"][item] = value
        else: 
            self.appliance[item] = value
    
    def get(self, item, default=None):
        try:
            return self[item]
        except (KeyError, IndexError):
            return default
    
    def getInt(self, item):
        return int(self.get(item,0))

    def getFloat(self, item):
        return float(self.get(item,0))

    def has(self, item, default=None):
        return self.get(item) != None

    def getProgramName(self):
        try:
            # Önce activity.attributes içinde ara
            activity = self._attributes.get("activity", {})
            if activity:
                program_name = activity.get("attributes", {}).get("programName")
                if program_name:
                    _LOGGER.debug(f"[{self._name}] Found program name in activity.attributes: {program_name}")
                    name = program_name.lower()
                    parts = name.split('.')
                    if len(parts) == 3:
                        return parts[2]
                    return name
            
            # Sonra direkt attributes içinde ara
            program_name = self._attributes.get("programName")
            if program_name:
                _LOGGER.debug(f"[{self._name}] Found program name in attributes: {program_name}")
                name = program_name.lower()
                parts = name.split('.')
                if len(parts) == 3:
                    return parts[2]
                return name
            
            # Sonra commandHistory içinde ara
            command_history = self._attributes.get("commandHistory", {})
            if command_history:
                command = command_history.get("command", {})
                program_name = command.get("programName")
                if program_name:
                    _LOGGER.debug(f"[{self._name}] Found program name in commandHistory: {program_name}")
                    name = program_name.lower()
                    parts = name.split('.')
                    if len(parts) == 3:
                        return parts[2]
                    return name
            
            _LOGGER.debug(f"[{self._name}] Program name not found in any location")
                
        except Exception as e:
            _LOGGER.warning(f"[{self._name}] Failed to get program name: {e}")
        
        return None

    """    
    async def load_context(self):
        data = await self._hon.async_get_context(self)
        #_LOGGER.warning(data)
        self._attributes = data
        for name, values in self._attributes.pop("shadow", {'NA': 0}).get("parameters").items():
            self._attributes.setdefault("parameters", {})[name] = values["parNewVal"]
    """
    async def load_context(self):
        data = await self._hon.async_get_context(self)
        self._attributes = data or {}

        shadow = self._attributes.pop("shadow", None)
        if not shadow:
            _LOGGER.warning("Unable to get device context: no shadow data in: %s", self._attributes)
            return

        parameters = shadow.get("parameters")
        if not parameters:
            _LOGGER.warning("Unable to get device context: no parameters in shadow data. %s", self._attributes)
            return

        for name, values in parameters.items():
            self._attributes.setdefault("parameters", {})[name] = values.get("parNewVal")
            
    @property
    def data(self):
        return {"attributes": self.attributes, "appliance": self.appliance, "statistics": self.statistics, **self.parameters}

    @property
    def appliance_type(self):
        return self._appliance.get("applianceTypeName")

    @property
    def mac_address(self):
        return self._appliance.get("macAddress")

    @property
    def model_name(self):
        return self._appliance.get("modelName")

    @property
    def name(self):
        return self._name

    @property
    def commands_options(self):
        return self._appliance_model.get("options")

    @property
    def commands(self):
        return self._commands
    
    @property
    def attributes(self):
        return self._attributes

    @property
    def statistics(self):
        return self._statistics

    @property
    def appliance(self):
        return self._appliance

    @property
    def settings(self):
        result = {}
        for name, command in self._commands.items():
            for key, setting in command.settings.items():
                result[f"{name}.{key}"] = setting
        return result

    @property
    def parameters(self):
        result = {}
        for name, command in self._commands.items():
            for key, parameter in command.parameters.items():
                result.setdefault(name, {})[key] = parameter.value
        return result
        
    """ 
    def update_command(self, command, parameters):
        for key in command.parameters.keys():
            if( key in parameters 
                and command.parameters.get(key).value != parameters.get(key) 
                and not isinstance(command.parameters.get(key), HonParameterFixed)):

                if( isinstance(command.parameters.get(key), HonParameterEnum) and parameters.get(key) not in command.parameters.get(key).values): 
                    _LOGGER.warning(f"Unable to update parameter [{key}] with value [{parameters.get(key)}] because not in range {command.parameters.get(key).values}. Use default instead.")
                else:
                    command.parameters.get(key).value = parameters.get(key) """

    def update_command(self, command, parameters):
        for key in command.parameters.keys():
            param = command.parameters.get(key)

            if (key not in parameters or isinstance(param, HonParameterFixed)):
                continue

            new_val = parameters.get(key)
            if param.value == new_val:
                continue

            try:
                param.value = new_val

            except Exception as e:
                _LOGGER.warning("Update_command: Invalid %s=%s (%s)", key, new_val, e)

                # 👉 fallback intelligent
                if hasattr(param, "default"):
                    try:
                        param.value = param.default
                        _LOGGER.warning("Update_command: Use Fallback %s -> default %s", key, param.default)
                    except Exception:
                        pass

    def settings_command(self, parameters = {}):
        if( "settings" not in self._commands ):
            raise ValueError("No command to update settings of the device")
        command = self._commands.get("settings")
        self.update_command(command, self.attributes.get("parameters", {}))
        self.update_command(command, parameters)

        # Update for next command (in case no refresh happens yet)
        for key in command.parameters.keys():
            self.attributes.setdefault("parameters", {})[key] = command.parameters.get(key).value

        return command

    def start_command(self, program = None, parameters = {}):
        if( "startProgram" not in self._commands ):
            raise ValueError("No command to start the device")
        command = self._commands.get("startProgram")
        if program is not None:
            command.set_program(program)
        # Return the new default command
        command = self._commands.get("startProgram")
        self.update_command(command, self.attributes.get("parameters", {}))
        self.update_command(command, parameters)
    
        # Update for next command (in case no refresh happens yet)
        for key in command.parameters.keys():
            self.attributes.setdefault("parameters", {})[key] = command.parameters.get(key).value

        return command

    def get_setting(self, setting_key):
        command_name, parameter_key = setting_key.split(".", 1)
        command = self._commands.get(command_name)
        if command is None:
            return None
        return command.settings.get(parameter_key)

    def has_current_setting(self, setting_key):
        command_name, parameter_key = setting_key.split(".", 1)
        command = self._commands.get(command_name)
        if command is None:
            return False
        return parameter_key in command.parameters

    def stop_command(self, parameters = {}):
        if( "stopProgram" in self._commands ):
            command = self._commands.get("stopProgram")
            self.update_command(command, self.attributes["parameters"])
            self.update_command(command, parameters)
            return command
        raise ValueError("No command to stop the device")

    async def load_commands(self):
        commands = await self._hon.load_commands(self._appliance)
    
        try:
            self._appliance_model = commands.pop("applianceModel")
        except:
            _LOGGER.error(f"Unable to load device commands. Please try to restart. Current value: [{commands}]")
            return

        for item in ["options", "dictionaryId"]:
            commands.pop(item)

        for command, attr in commands.items():
            if "parameters" in attr:
                self._commands[command] = HonCommand(command, attr, self._hon, self)
            if "setParameters" in attr and "parameters" in attr[list(attr)[0]]:
                self._commands[command] = HonCommand(command, attr.get("setParameters"), self._hon, self)
            elif "parameters" in attr[list(attr)[0]]:
                multi = {}
                for program, attr2 in attr.items():
                    program = program.split(".")[-1].lower()
                    cmd = HonCommand(command, attr2, self._hon, self, multi=multi, program=program)
                    multi[program] = cmd
                    self._commands[command] = cmd

    async def load_statistics(self):
        self._statistics = await self._hon.load_statistics(self)

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self._mac, self._type_name)
            },
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fw_version,
        }
