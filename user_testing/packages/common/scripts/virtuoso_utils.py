#!/usr/bin/env python3
"""
Common utilities for Virtuoso database operations in Heritrace.
"""

import subprocess
import time
import requests

DEFAULT_VIRTUOSO_HOST = "localhost"
DEFAULT_VIRTUOSO_PORT = 1111
DEFAULT_VIRTUOSO_USER = "dba"
DEFAULT_VIRTUOSO_PASSWORD = "dba"

def wait_for_virtuoso(host, max_retries=30, retry_interval=5):
    """
    Wait for Virtuoso SPARQL endpoint to be ready.
    
    Args:
        host: Virtuoso host
        max_retries: Maximum number of retries
        retry_interval: Interval between retries in seconds
        
    Returns:
        True if Virtuoso is ready, False otherwise
    """
    print(f"Waiting for Virtuoso at {host}:8890 to be ready...")
    
    for i in range(max_retries):
        try:
            response = requests.get(f"http://{host}:8890/sparql", timeout=5)
            if response.status_code == 200:
                print("✅ Virtuoso SPARQL endpoint is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(retry_interval)
    
    print("❌ Virtuoso SPARQL endpoint is not ready after maximum retries.")
    return False

def run_isql_command(args, sql_command, capture=True):
    """
    Run an ISQL command on the Virtuoso server.
    
    Args:
        args: Command line arguments with connection details
        sql_command: SQL command to execute
        capture: Whether to capture and return command output
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        command = [
            "/opt/virtuoso-opensource/bin/isql",
            f"{args.host}:{args.port}",
            args.user,
            args.password,
            f"EXEC={sql_command}"
        ]
        
        debug_cmd = command.copy()
        debug_cmd[3] = "******"
        print(f"Running ISQL command: {' '.join(debug_cmd)}")
        
        if capture:
            process = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return (
                process.returncode == 0,
                process.stdout,
                process.stderr
            )
        else:
            process = subprocess.run(command, check=False)
            return process.returncode == 0, "", ""
    except Exception as e:
        print(f"Error running ISQL command: {e}")
        return False, "", str(e)



def set_permissions(args):
    """
    Set database permissions for the Virtuoso database.
    
    Args:
        args: Command line arguments with connection details
        
    Returns:
        True if permissions were set successfully, False otherwise
    """
    print("Setting database permissions...")
    sql_command = """
    DB.DBA.RDF_DEFAULT_USER_PERMS_SET('nobody', 7);
    DB.DBA.USER_GRANT_ROLE('SPARQL', 'SPARQL_UPDATE');
    """
    success, stdout, stderr = run_isql_command(args, sql_command)
    
    if not success:
        print(f"❌ Failed to set database permissions:")
        print(stderr)
        return False
    
    print("✅ Database permissions set successfully.")
    return True
