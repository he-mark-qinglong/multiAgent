# tests/unit/test_condition_evaluator.py
import pytest
from core.condition_evaluator import ConditionEvaluator

class TestConditionEvaluator:
    def setup_method(self):
        self.evaluator = ConditionEvaluator()
        self.context = {
            "entities": {"power": True, "temperature": 25, "destination": "机场"},
            "session": {"user_id": "user_1"},
            "query": {"query_id": "q_1"},
            "custom": {},
            "runtime": {}
        }

    def test_var_resolution(self):
        """Test { var: path.to.value } resolution"""
        result = self.evaluator._resolve_var("entities.power", self.context)
        assert result == True

    def test_exists_true(self):
        condition = {"exists": {"var": "entities.temperature"}}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_exists_false(self):
        condition = {"exists": {"var": "entities.missing"}}
        assert self.evaluator.evaluate(condition, self.context) == False

    def test_eq_true(self):
        condition = {"==": [{"var": "entities.destination"}, "机场"]}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_eq_false(self):
        condition = {"==": [{"var": "entities.destination"}, "公司"]}
        assert self.evaluator.evaluate(condition, self.context) == False

    def test_and(self):
        condition = {"and": [
            {"exists": {"var": "entities.power"}},
            {"exists": {"var": "entities.temperature"}}
        ]}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_or(self):
        condition = {"or": [
            {"==": [{"var": "entities.destination"}, "公司"]},
            {"exists": {"var": "entities.temperature"}}
        ]}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_not(self):
        condition = {"not": {"==": [{"var": "entities.destination"}, "公司"]}}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_in(self):
        condition = {"in": [{"var": "entities.destination"}, ["机场", "公司", "天安门"]]}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_comparison_greater(self):
        condition = {">": [{"var": "entities.temperature"}, 24]}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_comparison_less(self):
        condition = {"<": [{"var": "entities.temperature"}, 30]}
        assert self.evaluator.evaluate(condition, self.context) == True