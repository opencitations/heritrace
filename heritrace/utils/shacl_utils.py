from typing import List

from heritrace.utils.shacl_display import (apply_display_rules,
                                           extract_shacl_form_fields,
                                           order_form_fields,
                                           process_nested_shapes)
from rdflib import Graph


def get_form_fields_from_shacl(shacl: Graph, display_rules: List[dict]):
    """
    Analizza le shape SHACL per estrarre i campi del form per ogni tipo di entità.

    Restituisce:
        OrderedDict: Un dizionario dove le chiavi sono i tipi di entità e i valori sono dizionari
                     dei campi del form con le loro proprietà.
    """
    if not shacl:
        return dict()

    # Step 1: Ottieni i campi iniziali dalle shape SHACL
    form_fields = extract_shacl_form_fields(shacl, display_rules)

    # Step 2: Processa le shape annidate per ogni campo
    processed_shapes = set()
    for entity_type in form_fields:
        for predicate in form_fields[entity_type]:
            for field_info in form_fields[entity_type][predicate]:
                if field_info.get("nodeShape"):
                    field_info["nestedShape"] = process_nested_shapes(
                        shacl,
                        display_rules,
                        field_info["nodeShape"],
                        processed_shapes=processed_shapes,
                    )

    # Step 3: Applica le regole di visualizzazione ai campi del form
    if display_rules:
        form_fields = apply_display_rules(shacl, form_fields, display_rules)
    
    # Step 4: Ordina i campi del form secondo le regole di visualizzazione
    ordered_form_fields = order_form_fields(form_fields, display_rules)

    return ordered_form_fields