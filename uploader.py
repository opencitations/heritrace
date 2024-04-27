import os
import argparse
from SPARQLWrapper import SPARQLWrapper, POST

def load_rdf_file_to_sparql(file_path, sparql_endpoint):
    absolute_file_path = os.path.abspath(file_path)
    normalized_file_path = absolute_file_path.replace("\\", "/")
    file_url = f"file:///{normalized_file_path}"

    sparql = SPARQLWrapper(sparql_endpoint)
    sparql.setMethod(POST)
    load_query = f"LOAD <{file_url}>"
    sparql.setQuery(load_query)
    sparql.query()

parser = argparse.ArgumentParser(
    description="Uploads RDF files from a specified directory to a given SPARQL endpoint using SPARQL LOAD."
)
parser.add_argument(
    "--directory",
    "-d",
    type=str,
    default="test/meta_subset",
    help="Path to the directory containing RDF files.",
)
parser.add_argument(
    "--endpoint",
    "-e",
    type=str,
    default="http://localhost:9999/blazegraph/sparql",
    help="SPARQL endpoint for the triple store.",
)

args = parser.parse_args()

for file_name in os.listdir(args.directory):
    file_path = os.path.join(args.directory, file_name)

    if os.path.isfile(file_path):
        try:
            print(f"Loading {file_name}...")
            load_rdf_file_to_sparql(file_path, args.endpoint)
            print("Loading completed.")
        except Exception as e:
            print(f"Error during the loading of {file_name}: {e}")