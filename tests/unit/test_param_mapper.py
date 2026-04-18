"""Tests for ParamMapper."""
import pytest
from core.param_mapper import ParamMapper


class TestParamMapper:
    def setup_method(self):
        self.mapper = ParamMapper()
        self.context = {
            "entities": {"temperature": "25", "fan_speed": 3, "mode": "cool"},
            "session": {},
            "query": {},
            "custom": {},
            "runtime": {}
        }

    def test_simple_param(self):
        """Test simple param without conversion."""
        param_defs = {
            "temperature": {"from": "entities.temperature"}
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["temperature"] == "25"

    def test_type_conversion(self):
        """Test type conversion to int."""
        param_defs = {
            "temperature": {"from": "entities.temperature", "type": "int"}
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["temperature"] == 25
        assert isinstance(result["temperature"], int)

    def test_default_value(self):
        """Test default value when entity exists."""
        param_defs = {
            "power": {"from": "entities.power", "default": True}
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["power"] is True

    def test_default_when_missing(self):
        """Test default value when entity is missing."""
        param_defs = {
            "volume": {"from": "entities.volume", "default": 50}
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["volume"] == 50

    def test_when_condition(self):
        """Test when condition - entity exists and passes."""
        param_defs = {
            "temp": {
                "from": "entities.temperature",
                "when": {"exists": {"var": "entities.temperature"}},
                "default": 24
            }
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["temp"] == "25"

    def test_when_condition_false_uses_default(self):
        """Test when condition fails, uses default."""
        param_defs = {
            "temp": {
                "from": "entities.missing",
                "when": {"exists": {"var": "entities.missing"}},
                "default": 24
            }
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["temp"] == 24

    def test_transform_celsius_to_fahrenheit(self):
        """Test temperature conversion transform."""
        param_defs = {
            "temp_f": {
                "from": "entities.temperature",
                "transform": "celsius_to_fahrenheit"
            }
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["temp_f"] == 77.0  # 25°C = 77°F

    def test_omit_if_missing(self):
        """Test omit_if_missing excludes missing params."""
        param_defs = {
            "missing_param": {
                "from": "entities.does_not_exist",
                "omit_if_missing": True
            }
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert "missing_param" not in result
