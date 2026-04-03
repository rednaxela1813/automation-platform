from __future__ import annotations

import json

from automation.config import parser_rules


def test_load_parser_rules_returns_empty_when_disabled(monkeypatch):
    parser_rules.load_parser_rules.cache_clear()
    monkeypatch.setattr(parser_rules.settings, "parser_rules_enabled", False)

    assert parser_rules.load_parser_rules() == {}


def test_load_parser_rules_returns_empty_when_file_missing(monkeypatch, tmp_path):
    parser_rules.load_parser_rules.cache_clear()
    monkeypatch.setattr(parser_rules.settings, "parser_rules_enabled", True)
    monkeypatch.setattr(parser_rules.settings, "parser_rules_file", str(tmp_path / "missing.json"))

    assert parser_rules.load_parser_rules() == {}


def test_load_parser_rules_reads_json_object(monkeypatch, tmp_path):
    parser_rules.load_parser_rules.cache_clear()
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps({"pdf": {"patterns": {"amount": ["a"]}}}), encoding="utf-8")
    monkeypatch.setattr(parser_rules.settings, "parser_rules_enabled", True)
    monkeypatch.setattr(parser_rules.settings, "parser_rules_file", str(rules_path))

    assert parser_rules.load_parser_rules()["pdf"]["patterns"]["amount"] == ["a"]
    assert parser_rules.get_parser_rule_section("pdf") == {"patterns": {"amount": ["a"]}}


def test_load_parser_rules_returns_empty_for_invalid_payload(monkeypatch, tmp_path):
    parser_rules.load_parser_rules.cache_clear()
    rules_path = tmp_path / "rules.json"
    rules_path.write_text('["not-an-object"]', encoding="utf-8")
    monkeypatch.setattr(parser_rules.settings, "parser_rules_enabled", True)
    monkeypatch.setattr(parser_rules.settings, "parser_rules_file", str(rules_path))

    assert parser_rules.load_parser_rules() == {}
    assert parser_rules.get_parser_rule_section("missing") == {}
