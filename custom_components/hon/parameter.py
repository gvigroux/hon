#All credits to https://github.com/Andre0512/pyhOn

import logging
_LOGGER = logging.getLogger(__name__)

class HonParameter:
    def __init__(self, key, attributes):
        self._key = key
        self._category = attributes.get("category")
        self._typology = attributes.get("typology")
        self._mandatory = attributes.get("mandatory")
        self._value = ""

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value if self._value is not None else "0"

    @property
    def category(self):
        return self._category

    @property
    def typology(self):
        return self._typology

    @property
    def mandatory(self):
        return self._mandatory


class HonParameterFixed(HonParameter):
    def __init__(self, key, attributes):
        super().__init__(key, attributes)
        self._value = attributes.get("fixedValue", None)

    def __repr__(self):
        return f"{self.__class__} (<{self.key}> fixed)"

    @property
    def value(self):
        return self._value if self._value is not None else "0"

    @value.setter
    def value(self, value):
        if not value == self._value:
            raise ValueError(f"Can't change fixed value for parameter: {self.key}. Fixed value: {self._value}. New value {value}.")


class HonParameterRange(HonParameter):
    def __init__(self, key, attributes):
        super().__init__(key, attributes)
        try:
            self._min = int(attributes["minimumValue"])
            self._max = int(attributes["maximumValue"])
            self._step = int(attributes["incrementValue"])
            self._default = int(attributes.get("defaultValue", self._min))
        except (TypeError, ValueError):
            self._min = float(attributes["minimumValue"].replace(",","."))
            self._max = float(attributes["maximumValue"].replace(",","."))
            self._step = float(attributes["incrementValue"].replace(",","."))
            self._default = float(attributes.get("defaultValue", self._min).replace(",","."))
        self._value = self._default
        #_LOGGER.error(f"Param {key} min {self._min} | max {self._max} | step {self._step} | default {self._default}")

    def __repr__(self):
        return f"{self.__class__} (<{self.key}> [{self._min} - {self._max}])"

    def dump(self):
        return f"{self.key}: \t\t[{self._min} - {self._max}] - Default: {self._default} - Step: {self._step}"

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def step(self):
        return self._step

    @property
    def default(self):
        return self._default

    @property
    def value(self):
        return self._value if self._value is not None else self._min

    @value.setter
    def value(self, value):
        if type(value) == str and type(self._step) == float:
            value = float(value.replace(",","."))
        elif type(value) == str:
            value = int(float(value.replace(",",".")))

        if self._min <= value <= self._max and not value % self._step:
            self._value = value
        else:
            raise ValueError(f"Key [{self.key}] Value [{value}] - Allowed: min {self._min} max {self._max} step {self._step}")


class HonParameterEnum(HonParameter):
    def __init__(self, key, attributes):
        super().__init__(key, attributes)
        self._default = attributes.get("defaultValue")
        self._value = self._default or "0"
        self._values = attributes.get("enumValues")

    def __repr__(self):
        return f"{self.__class__} (<{self.key}> {self.values})"
        
    def dump(self):
        return f"{self.key}: {self.valuesBase} - Default: {self._default}"

    @property
    def default(self):
        return self._default

    @property
    def values(self):
        return sorted([str(value) for value in self._values])

    @property
    def valuesBase(self):
        return sorted(self._values)

    @property
    def value(self):
        return self._value if self._value is not None else self.values[0]

    @value.setter
    def value(self, value):
        if value in self.values:
            self._value = value
        else:
            raise ValueError(f"ParameterEnum [{self.key}] Invalid value: {value} Allowed values: {self.values}")


class HonParameterProgram(HonParameterEnum):
    def __init__(self, key, command):
        super().__init__(key, {})
        self._command = command
        self._value = command._program
        self._values = command._multi
        self._typology = "enum"

    def dump(self):
        return f"{self.key}: {self.value}"

    @property
    def default(self):
        return self._value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if value in self.values:
            self._command.set_program(value)
        else:
            raise ValueError(f"Allowed values {self._values}")