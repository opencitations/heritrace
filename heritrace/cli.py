# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import os
from pathlib import Path

import click
from flask import Flask


def register_cli_commands(app: Flask) -> None:
    @app.cli.group()
    def translate() -> None:
        """Translation and localization commands."""

    @translate.command()
    def update() -> None:
        """Update all languages."""
        if os.system(
            "pybabel extract -F babel/babel.cfg -k lazy_gettext -o babel/messages.pot ."
        ):
            msg = "extract command failed"
            raise RuntimeError(msg)
        if os.system("pybabel update -i babel/messages.pot -d babel/translations"):
            msg = "update command failed"
            raise RuntimeError(msg)
        Path("babel/messages.pot").unlink()

    @translate.command("compile")
    def compile_translations() -> None:
        """Compile all languages."""
        if os.system("pybabel compile -d babel/translations"):
            msg = "compile command failed"
            raise RuntimeError(msg)

    @translate.command()
    @click.argument("lang")
    def init(lang: str) -> None:
        """Initialize a new language."""
        if os.system("pybabel extract -F babel/babel.cfg -k _l -o messages.pot ."):
            msg = "extract command failed"
            raise RuntimeError(msg)
        if os.system("pybabel init -i messages.pot -d babel/translations -l " + lang):
            msg = "init command failed"
            raise RuntimeError(msg)
        Path("messages.pot").unlink()
