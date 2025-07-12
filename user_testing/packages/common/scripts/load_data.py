#!/usr/bin/env python3
"""
Script to load RDF data into Virtuoso for Heritrace end-user testing.
"""

import argparse
import glob
import os
import sys
import configparser

import requests

from virtuoso_utils import (
    DEFAULT_VIRTUOSO_HOST,
    DEFAULT_VIRTUOSO_PORT,
    DEFAULT_VIRTUOSO_USER,
    DEFAULT_VIRTUOSO_PASSWORD,
    wait_for_virtuoso,
    run_isql_command,
    setup_fulltext_indexing,
    set_permissions
)

DATA_DIR = "/data"
DEFAULT_GRAPH = "https://w3id.org/oc/meta/br/"
NQ_GZ_PATTERN = "*.nq.gz"


def find_nquads_files(directory):
    """
    Find all .nq.gz files in the specified directory.
    
    Args:
        directory: Directory to search in
        
    Returns:
        List of file paths
    """
    pattern = os.path.join(directory, NQ_GZ_PATTERN)
    return glob.glob(pattern)


def check_dirs_allowed(args):
    """
    Check if the DirsAllowed setting in Virtuoso includes the data directory by analyzing virtuoso.ini.
    
    Args:
        args: Command line arguments with connection details
        
    Returns:
        True if the data directory is allowed, False otherwise
    """
    try:
        
        virtuoso_ini_path = '/database/virtuoso.ini'
        
        if not os.path.exists(virtuoso_ini_path):
            print(f"Warning: virtuoso.ini not found at {virtuoso_ini_path}")
            return True
        
        config = configparser.ConfigParser(strict=False)
        config.read(virtuoso_ini_path)
        
        dirs_allowed = None
        for section in config.sections():
            if 'DirsAllowed' in config[section]:
                dirs_allowed = config[section]['DirsAllowed']
                break
        
        if dirs_allowed:
            print(f"DirsAllowed setting from virtuoso.ini: {dirs_allowed}")
            
            allowed_dirs = [d.strip() for d in dirs_allowed.split(',')]
            
            for allowed_dir in allowed_dirs:
                if args.data_dir.startswith(allowed_dir):
                    print(f"✅ Data directory {args.data_dir} is allowed (under {allowed_dir})")
                    return True
            
            print(f"❌ Data directory {args.data_dir} is NOT in DirsAllowed setting")
            return False
        else:
            print("DirsAllowed setting not found in virtuoso.ini")
    except Exception as e:
        print(f"Error checking DirsAllowed: {e}")
    
    return True


def check_data_loaded(host, graph_uri):
    """
    Check if data is already loaded in the specified graph.
    
    Args:
        host: Virtuoso host
        graph_uri: Graph URI to check
        
    Returns:
        True if data is already loaded, False otherwise
    """
    try:
        query = f"""SELECT COUNT(*) AS ?count WHERE {{ GRAPH <{graph_uri}> {{ ?s ?p ?o }} }} LIMIT 1"""
        
        params = {
            'query': query,
            'format': 'application/sparql-results+json'
        }
        
        response = requests.get(f"http://{host}:8890/sparql", params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            bindings = data.get('results', {}).get('bindings', [])
            if bindings and 'count' in bindings[0]:
                count = int(bindings[0]['count']['value'])
                return count > 0
    except Exception as e:
        print(f"Error checking if data is loaded: {e}")
    
    return False


def main():
    """
    Main function to load data into Virtuoso.
    """
    parser = argparse.ArgumentParser(
        description="Load N-Quads Gzipped files into Virtuoso for Heritrace end-user testing."
    )
    
    parser.add_argument("-d", "--data-dir", default=DATA_DIR,
                        help=f"Directory containing .nq.gz files (Default: {DATA_DIR}).")
    parser.add_argument("-H", "--host", default=DEFAULT_VIRTUOSO_HOST,
                        help=f"Virtuoso server host (Default: {DEFAULT_VIRTUOSO_HOST}).")
    parser.add_argument("-P", "--port", type=int, default=DEFAULT_VIRTUOSO_PORT,
                        help=f"Virtuoso server ISQL port (Default: {DEFAULT_VIRTUOSO_PORT}).")
    parser.add_argument("-u", "--user", default=DEFAULT_VIRTUOSO_USER,
                        help=f"Virtuoso username (Default: {DEFAULT_VIRTUOSO_USER}).")
    parser.add_argument("-k", "--password", default=DEFAULT_VIRTUOSO_PASSWORD,
                        help=f"Virtuoso password (Default: {DEFAULT_VIRTUOSO_PASSWORD}).")
    parser.add_argument("-g", "--graph", default=DEFAULT_GRAPH,
                        help=f"Default graph to load data into (Default: {DEFAULT_GRAPH}).")
    
    args = parser.parse_args()
    
    if not wait_for_virtuoso(args.host):
        print("❌ Virtuoso is not ready. Exiting.")
        sys.exit(1)
    
    print("Checking Virtuoso DirsAllowed configuration...")
    if not check_dirs_allowed(args):
        print("⚠️ Warning: Data directory may not be in DirsAllowed. Will attempt to continue anyway.")
    
    print(f"Checking if data is already loaded in graph <{args.graph}>...")
    if check_data_loaded(args.host, args.graph):
        print("✅ Data is already loaded. Skipping data loading.")        
        sys.exit(0)
    
    print(f"Looking for .nq.gz files in {args.data_dir}...")
    files = find_nquads_files(args.data_dir)
    
    if not files:
        print(f"❌ No .nq.gz files found in {args.data_dir}")
        sys.exit(1)
    
    print(f"Found {len(files)} .nq.gz files.")
    print(f"Registering files with Virtuoso using ld_dir...")
    data_dir_sql_escaped = args.data_dir.replace("'", "''")
    file_pattern_sql_escaped = NQ_GZ_PATTERN.replace("'", "''")
    
    sql_command = f"""ld_dir('{data_dir_sql_escaped}', '{file_pattern_sql_escaped}', '{args.graph}');"""
    success, stdout, stderr = run_isql_command(args, sql_command)
    
    if not success:
        print(f"❌ Failed to register files using ld_dir:")
        print("This may be due to DirsAllowed not including the data directory.")
        print("Please ensure the data directory is included in DirsAllowed in virtuoso.ini.")
        sys.exit(1)
    
    print("Starting RDF loader...")
    sql_command = "rdf_loader_run();"
    success, stdout, stderr = run_isql_command(args, sql_command)
    
    if not success:
        print(f"❌ Failed to run RDF loader:")
        sys.exit(1)
    
    print("✅ RDF loader completed successfully.")
    
    print("Setting up full-text indexing...")
    if not setup_fulltext_indexing(args):
        print("❌ Failed to set up full-text indexing. Exiting.")
        sys.exit(1)
    
    print("Setting database permissions...")
    if not set_permissions(args):
        print("❌ Failed to set permissions. Exiting.")
        sys.exit(1)
        
    print("✅ Full-text indexing completed successfully.")
    print("✅ Data loading completed successfully.")
    print("ℹ️ Note: For optimal performance, consider restarting Virtuoso after this operation.")


if __name__ == "__main__":
    main()