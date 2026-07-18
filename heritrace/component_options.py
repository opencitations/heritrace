# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
import os
from typing import cast


def load_component_options(environment_variable: str) -> dict[str, object]:
    if environment_variable not in os.environ:
        return {}

    try:
        options: object = json.loads(os.environ[environment_variable])
    except json.JSONDecodeError as error:
        msg = f"{environment_variable} must contain a valid JSON object"
        raise ValueError(msg) from error

    if not isinstance(options, dict):
        msg = f"{environment_variable} must contain a JSON object"
        raise TypeError(msg)

    return cast("dict[str, object]", options)
