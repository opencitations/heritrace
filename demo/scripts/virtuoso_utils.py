# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import argparse
import subprocess
import time
from http import HTTPStatus

import requests

DEFAULT_VIRTUOSO_HOST = "localhost"
DEFAULT_VIRTUOSO_PORT = 1111
DEFAULT_VIRTUOSO_USER = "dba"
DEFAULT_VIRTUOSO_PASSWORD = "dba"


def wait_for_virtuoso(
    host: str, max_retries: int = 30, retry_interval: int = 5
) -> bool:
    print(f"Waiting for Virtuoso at {host}:8890 to be ready...")

    for _i in range(max_retries):
        try:
            response = requests.get(f"http://{host}:8890/sparql", timeout=5)
            if response.status_code == HTTPStatus.OK:
                print("Virtuoso SPARQL endpoint is ready.")
                return True
        except requests.exceptions.RequestException:
            pass

        time.sleep(retry_interval)

    print("Virtuoso SPARQL endpoint is not ready after maximum retries.")
    return False


def run_isql_command(
    args: argparse.Namespace, sql_command: str, *, capture: bool = True
) -> tuple[bool, str, str]:
    try:
        command = [
            "/opt/virtuoso-opensource/bin/isql",
            f"{args.host}:{args.port}",
            args.user,
            args.password,
            f"EXEC={sql_command}",
        ]

        debug_cmd = command.copy()
        debug_cmd[3] = "******"
        print(f"Running ISQL command: {' '.join(debug_cmd)}")

        if capture:
            process = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
            result = (process.returncode == 0, process.stdout, process.stderr)
        else:
            process = subprocess.run(command, check=False)
            result = (process.returncode == 0, "", "")
    except (OSError, subprocess.SubprocessError) as e:
        print(f"Error running ISQL command: {e}")
        return False, "", str(e)
    else:
        return result


def set_permissions(args: argparse.Namespace) -> bool:
    print("Setting database permissions...")
    sql_command = """
    DB.DBA.RDF_DEFAULT_USER_PERMS_SET('nobody', 7);
    DB.DBA.USER_GRANT_ROLE('SPARQL', 'SPARQL_UPDATE');
    """
    success, _stdout, stderr = run_isql_command(args, sql_command)

    if not success:
        print("Failed to set database permissions:")
        print(stderr)
        return False

    print("Database permissions set successfully.")
    return True
