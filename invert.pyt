import json

def invert_dictionary(d):
    """Inverte le chiavi e i valori di un dizionario."""
    return {v: k for k, v in d.items()}

def invert_json_file(input_filename, output_filename):
    """Legge un file JSON, inverte le chiavi e i valori, e scrive il risultato in un altro file."""
    with open(input_filename, 'r') as infile:
        data = json.load(infile)
        
        # Inverti le chiavi e i valori per ogni elemento nel dizionario
        inverted_data = {key: invert_dictionary(value) for key, value in data.items()}

    with open(output_filename, 'w') as outfile:
        json.dump(inverted_data, outfile, indent=4)

# Usa la funzione
input_file = "resources/context.json"
output_file = "resources/output.json"
invert_json_file(input_file, output_file)
