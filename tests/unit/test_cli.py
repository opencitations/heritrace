import os
import pytest
from unittest.mock import patch
from flask import Flask
from heritrace.cli import register_cli_commands


@pytest.fixture
def app():
    app = Flask(__name__)
    register_cli_commands(app)
    return app


def test_translate_group_exists(app):
    """Test that the translate command group exists"""
    runner = app.test_cli_runner()
    result = runner.invoke(args=["translate"])
    assert result.exit_code == 0
    assert "Translation and localization commands" in result.output


@patch("os.system")
@patch("os.remove")
def test_translate_update(mock_remove, mock_system, app):
    """Test the translate update command"""
    mock_system.return_value = 0
    runner = app.test_cli_runner()

    result = runner.invoke(args=["translate", "update"])

    assert result.exit_code == 0
    assert mock_system.call_count == 2
    mock_remove.assert_called_once_with("babel/messages.pot")


@patch("os.system")
@patch("os.remove")
def test_translate_update_extract_failure(mock_remove, mock_system, app):
    """Test the translate update command when extract fails"""
    mock_system.side_effect = [1]  # First command fails
    runner = app.test_cli_runner()

    result = runner.invoke(args=["translate", "update"])

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "extract command failed"
    mock_remove.assert_not_called()


@patch("os.system")
@patch("os.remove")
def test_translate_update_update_failure(mock_remove, mock_system, app):
    """Test the translate update command when update fails"""
    mock_system.side_effect = [0, 1]  # Second command fails
    runner = app.test_cli_runner()

    result = runner.invoke(args=["translate", "update"])

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "update command failed"
    mock_remove.assert_not_called()


@patch("os.system")
def test_translate_compile(mock_system, app):
    """Test the translate compile command"""
    mock_system.return_value = 0
    runner = app.test_cli_runner()

    result = runner.invoke(args=["translate", "compile"])

    assert result.exit_code == 0
    mock_system.assert_called_once()


@patch("os.system")
def test_translate_compile_failure(mock_system, app):
    """Test the translate compile command when it fails"""
    mock_system.return_value = 1
    runner = app.test_cli_runner()

    result = runner.invoke(args=["translate", "compile"])

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "compile command failed"


@patch("os.system")
@patch("os.remove")
def test_translate_init(mock_remove, mock_system, app):
    """Test the translate init command"""
    mock_system.return_value = 0
    runner = app.test_cli_runner()

    result = runner.invoke(args=["translate", "init", "it"])

    assert result.exit_code == 0
    assert mock_system.call_count == 2
    mock_remove.assert_called_once_with("messages.pot")


@patch("os.system")
@patch("os.remove")
def test_translate_init_extract_failure(mock_remove, mock_system, app):
    """Test the translate init command when extract fails"""
    mock_system.side_effect = [1]  # First command fails
    runner = app.test_cli_runner()

    result = runner.invoke(args=["translate", "init", "it"])

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "extract command failed"
    mock_remove.assert_not_called()


@patch("os.system")
@patch("os.remove")
def test_translate_init_init_failure(mock_remove, mock_system, app):
    """Test the translate init command when init fails"""
    mock_system.side_effect = [0, 1]  # Second command fails
    runner = app.test_cli_runner()

    result = runner.invoke(args=["translate", "init", "it"])

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "init command failed"
    mock_remove.assert_not_called()
