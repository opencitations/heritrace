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

def setup_fulltext_indexing(args):
    """
    Set up full-text indexing for the Virtuoso database.
    
    Args:
        args: Command line arguments with connection details
        
    Returns:
        True if setup was successful, False otherwise
    """
    print("Setting up full-text indexing...")
    
    print("1. Dropping existing full-text index tables if they exist...")
    sql_command = """
    drop table DB.DBA.VTLOG_DB_DBA_RDF_OBJ;
    drop table DB.DBA.RDF_OBJ_RO_FLAGS_WORDS;
    """
    success, stdout, stderr = run_isql_command(args, sql_command)
    
    print("2. Adding full-text indexing rules...")
    sql_command = "DB.DBA.RDF_OBJ_FT_RULE_ADD(null, null, 'All literals');"
    success, stdout, stderr = run_isql_command(args, sql_command)
    
    if not success:
        print(f"❌ Failed to add full-text indexing rules:")
        print(stderr)
        return False
    
    print("3. Creating full-text index structure...")
    sql_command = """
    DB.DBA.vt_create_text_index (
      fix_identifier_case ('DB.DBA.RDF_OBJ'),
      fix_identifier_case ('RO_FLAGS'),
      fix_identifier_case ('RO_ID'),
      0, 0, vector (), 1, '*ini*', 'UTF-8-QR');
    """
    success, stdout, stderr = run_isql_command(args, sql_command)
    
    if not success:
        print(f"❌ Failed to create full-text index structure:")
        print(stderr)
        return False
    
    print("4. Enabling batch updates for the index...")
    sql_command = "DB.DBA.vt_batch_update (fix_identifier_case ('DB.DBA.RDF_OBJ'), 'ON', 1);"
    success, stdout, stderr = run_isql_command(args, sql_command)
    
    if not success:
        print(f"❌ Failed to enable batch updates for the index:")
        print(stderr)
        return False
    
    print("5. Filling the full-text index...")
    sql_command = "DB.DBA.RDF_OBJ_FT_RECOVER();"
    success, stdout, stderr = run_isql_command(args, sql_command)
    
    if not success:
        print(f"❌ Failed to fill the full-text index:")
        print(stderr)
        return False
    
    return True

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
