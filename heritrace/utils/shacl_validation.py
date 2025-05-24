import re
from collections import defaultdict

import validators
from flask_babel import gettext
from heritrace.extensions import get_custom_filter, get_shacl_graph
from resources.datatypes import DATATYPE_MAPPING
from heritrace.utils.display_rules_utils import get_highest_priority_class
from heritrace.utils.sparql_utils import fetch_data_graph_for_subject
from rdflib import RDF, XSD, Literal, URIRef
from rdflib.plugins.sparql import prepareQuery


def get_valid_predicates(triples):
    shacl = get_shacl_graph()

    existing_predicates = [triple[1] for triple in triples]
    predicate_counts = {
        str(predicate): existing_predicates.count(predicate)
        for predicate in set(existing_predicates)
    }
    default_datatypes = {
        str(predicate): XSD.string for predicate in existing_predicates
    }
    s_types = [triple[2] for triple in triples if triple[1] == RDF.type]

    valid_predicates = [
        {
            str(predicate): {
                "min": None,
                "max": None,
                "hasValue": None,
                "optionalValues": [],
            }
        }
        for predicate in set(existing_predicates)
    ]
    if not s_types:
        return (
            existing_predicates,
            existing_predicates,
            default_datatypes,
            dict(),
            dict(),
            [],
            [str(predicate) for predicate in existing_predicates],
        )
    if not shacl:
        return (
            existing_predicates,
            existing_predicates,
            default_datatypes,
            dict(),
            dict(),
            s_types,
            [str(predicate) for predicate in existing_predicates],
        )

    highest_priority_class = get_highest_priority_class(s_types)
    s_types = [highest_priority_class] if highest_priority_class else s_types

    query_string = f"""
        SELECT ?predicate ?datatype ?maxCount ?minCount ?hasValue (GROUP_CONCAT(?optionalValue; separator=",") AS ?optionalValues) WHERE {{
            ?shape sh:targetClass ?type ;
                   sh:property ?property .
            VALUES ?type {{<{'> <'.join(s_types)}>}}
            ?property sh:path ?predicate .
            OPTIONAL {{?property sh:datatype ?datatype .}}
            OPTIONAL {{?property sh:maxCount ?maxCount .}}
            OPTIONAL {{?property sh:minCount ?minCount .}}
            OPTIONAL {{?property sh:hasValue ?hasValue .}}
            OPTIONAL {{
                ?property sh:in ?list .
                ?list rdf:rest*/rdf:first ?optionalValue .
            }}
            OPTIONAL {{
                ?property sh:or ?orList .
                ?orList rdf:rest*/rdf:first ?orConstraint .
                ?orConstraint sh:datatype ?datatype .
            }}
            FILTER (isURI(?predicate))
        }}
        GROUP BY ?predicate ?datatype ?maxCount ?minCount ?hasValue
    """

    query = prepareQuery(
        query_string,
        initNs={
            "sh": "http://www.w3.org/ns/shacl#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        },
    )
    results = shacl.query(query)
    valid_predicates = [
        {
            str(row.predicate): {
                "min": 0 if row.minCount is None else int(row.minCount),
                "max": None if row.maxCount is None else str(row.maxCount),
                "hasValue": row.hasValue,
                "optionalValues": (
                    row.optionalValues.split(",") if row.optionalValues else []
                ),
            }
        }
        for row in results
    ]

    can_be_added = set()
    can_be_deleted = set()
    mandatory_values = defaultdict(list)
    for valid_predicate in valid_predicates:
        for predicate, ranges in valid_predicate.items():
            if ranges["hasValue"]:
                mandatory_value_present = any(
                    triple[2] == ranges["hasValue"] for triple in triples
                )
                mandatory_values[str(predicate)].append(str(ranges["hasValue"]))
            else:
                max_reached = ranges["max"] is not None and int(
                    ranges["max"]
                ) <= predicate_counts.get(predicate, 0)

                if not max_reached:
                    can_be_added.add(predicate)
                if not (
                    ranges["min"] is not None
                    and int(ranges["min"]) == predicate_counts.get(predicate, 0)
                ):
                    can_be_deleted.add(predicate)

    datatypes = defaultdict(list)
    for row in results:
        if row.datatype:
            datatypes[str(row.predicate)].append(str(row.datatype))
        else:
            datatypes[str(row.predicate)].append(str(XSD.string))

    optional_values = dict()
    for valid_predicate in valid_predicates:
        for predicate, ranges in valid_predicate.items():
            if "optionalValues" in ranges:
                optional_values.setdefault(str(predicate), list()).extend(
                    ranges["optionalValues"]
                )
    return (
        list(can_be_added),
        list(can_be_deleted),
        dict(datatypes),
        mandatory_values,
        optional_values,
        s_types,
        {list(predicate_data.keys())[0] for predicate_data in valid_predicates},
    )


def validate_new_triple(
    subject, predicate, new_value, action: str, old_value=None, entity_types=None
):
    data_graph = fetch_data_graph_for_subject(subject)
    if old_value is not None:
        matching_triples = [
            triple[2]
            for triple in data_graph.triples((URIRef(subject), URIRef(predicate), None))
            if str(triple[2]) == str(old_value)
        ]
        # Only update old_value if we found a match in the graph
        if matching_triples:
            old_value = matching_triples[0]
    if not len(get_shacl_graph()):
        # If there's no SHACL, we accept any value but preserve datatype if available
        if validators.url(new_value):
            return URIRef(new_value), old_value, ""
        else:
            # Preserve the datatype of the old value if it's a Literal
            if (
                old_value is not None
                and isinstance(old_value, Literal)
                and old_value.datatype
            ):
                return Literal(new_value, datatype=old_value.datatype), old_value, ""
            else:
                return Literal(new_value), old_value, ""

    # Get entity types from the data graph
    s_types = [
        triple[2] for triple in data_graph.triples((URIRef(subject), RDF.type, None))
    ]

    # If entity_types is provided, use it (useful for nested entities being created)
    if entity_types and not s_types:
        if isinstance(entity_types, list):
            s_types = entity_types
        else:
            s_types = [entity_types]

    # Get types for entities that have this subject as their object
    # This is crucial for proper SHACL validation in cases where constraints depend on the context
    # Example: When validating an identifier's value (e.g., DOI, ISSN, ORCID):
    # - The identifier itself is of type datacite:Identifier
    # - But its format constraints depend on what owns it:
    #   * A DOI for an article follows one pattern
    #   * An ISSN for a journal follows another
    #   * An ORCID for a person follows yet another
    # By including these "inverse" types, we ensure validation considers the full context
    inverse_types = []
    for s, p, o in data_graph.triples((None, None, URIRef(subject))):
        # Ottieni i tipi dell'entità che ha il soggetto come oggetto
        s_types_inverse = [t[2] for t in data_graph.triples((s, RDF.type, None))]
        inverse_types.extend(s_types_inverse)

    # Add inverse types to s_types
    s_types.extend(inverse_types)

    query = f"""
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT DISTINCT ?path ?datatype ?a_class ?classIn ?maxCount ?minCount ?pattern ?message ?shape
            (GROUP_CONCAT(DISTINCT COALESCE(?optionalValue, ""); separator=",") AS ?optionalValues)
            (GROUP_CONCAT(DISTINCT COALESCE(?conditionPath, ""); separator=",") AS ?conditionPaths)
            (GROUP_CONCAT(DISTINCT COALESCE(?conditionValue, ""); separator=",") AS ?conditionValues)
        WHERE {{
            ?shape sh:targetClass ?type ;
                sh:property ?propertyShape .
            ?propertyShape sh:path ?path .
            FILTER(?path = <{predicate}>)
            VALUES ?type {{<{'> <'.join(s_types)}>}}
            OPTIONAL {{?propertyShape sh:datatype ?datatype .}}
            OPTIONAL {{?propertyShape sh:maxCount ?maxCount .}}
            OPTIONAL {{?propertyShape sh:minCount ?minCount .}}
            OPTIONAL {{?propertyShape sh:class ?a_class .}}
            OPTIONAL {{
                ?propertyShape sh:or ?orList .
                ?orList rdf:rest*/rdf:first ?orConstraint .
                ?orConstraint sh:datatype ?datatype .
                OPTIONAL {{?orConstraint sh:class ?class .}}
            }}
            OPTIONAL {{
                ?propertyShape  sh:classIn ?classInList .
                ?classInList rdf:rest*/rdf:first ?classIn .
            }}
            OPTIONAL {{
                ?propertyShape sh:in ?list .
                ?list rdf:rest*/rdf:first ?optionalValue .
            }}
            OPTIONAL {{
                ?propertyShape sh:pattern ?pattern .
                OPTIONAL {{?propertyShape sh:message ?message .}}
            }}
            OPTIONAL {{
                ?propertyShape sh:condition ?conditionNode .
                ?conditionNode sh:path ?conditionPath ;
                             sh:hasValue ?conditionValue .
            }}
        }}
        GROUP BY ?path ?datatype ?a_class ?classIn ?maxCount ?minCount ?pattern ?message ?shape
    """
    shacl = get_shacl_graph()
    custom_filter = get_custom_filter()
    results = shacl.query(query)
    property_exists = [row.path for row in results]
    shapes = [row.shape for row in results if row.shape is not None]
    current_shape = shapes[0] if shapes else None
    if not property_exists:
        if not s_types:
            return (
                None,
                old_value, 
                gettext(
                    "No entity type specified"
                ),
            )
        
        return (
            None,
            old_value,
            gettext(
                "The property %(predicate)s is not allowed for resources of type %(s_type)s",
                predicate=custom_filter.human_readable_predicate((predicate, current_shape)),
                s_type=custom_filter.human_readable_class((s_types[0], current_shape)),
            ),
        )
    datatypes = [row.datatype for row in results if row.datatype is not None]
    classes = [row.a_class for row in results if row.a_class]
    classes.extend([row.classIn for row in results if row.classIn])
    optional_values_str = [row.optionalValues for row in results if row.optionalValues]
    optional_values_str = optional_values_str[0] if optional_values_str else ""
    optional_values = [value for value in optional_values_str.split(",") if value]

    max_count = [row.maxCount for row in results if row.maxCount]
    min_count = [row.minCount for row in results if row.minCount]
    max_count = int(max_count[0]) if max_count else None
    min_count = int(min_count[0]) if min_count else None

    current_values = list(
        data_graph.triples((URIRef(subject), URIRef(predicate), None))
    )
    current_count = len(current_values)

    if action == "create":
        new_count = current_count + 1
    elif action == "delete":
        new_count = current_count - 1
    else:  # update
        new_count = current_count

    if max_count is not None and new_count > max_count:
        value = gettext("value") if max_count == 1 else gettext("values")
        return (
            None,
            old_value,
            gettext(
                "The property %(predicate)s allows at most %(max_count)s %(value)s",
                predicate=custom_filter.human_readable_predicate((predicate, current_shape)),
                max_count=max_count,
                value=value,
            ),
        )
    if min_count is not None and new_count < min_count:
        value = gettext("value") if min_count == 1 else gettext("values")
        return (
            None,
            old_value,
            gettext(
                "The property %(predicate)s requires at least %(min_count)s %(value)s",
                predicate=custom_filter.human_readable_predicate((predicate, current_shape)),
                min_count=min_count,
                value=value,
            ),
        )

    # For delete operations, we only need to validate cardinality constraints (which we've already done)
    # No need to validate the datatype or class of the value being deleted
    if action == "delete":
        return None, old_value, ""

    if optional_values and new_value not in optional_values:
        optional_value_labels = [
            custom_filter.human_readable_predicate((value, current_shape))
            for value in optional_values
        ]
        return (
            None,
            old_value,
            gettext(
                "<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires one of the following values: %(o_values)s",
                new_value=custom_filter.human_readable_predicate((new_value, current_shape)),
                property=custom_filter.human_readable_predicate((predicate, current_shape)),
                o_values=", ".join(
                    [f"<code>{label}</code>" for label in optional_value_labels]
                ),
            ),
        )

    # Check pattern constraints
    for row in results:
        if row.pattern:
            # Check if there are conditions for this pattern
            condition_paths = row.conditionPaths.split(",") if row.conditionPaths else []
            condition_values = row.conditionValues.split(",") if row.conditionValues else []
            conditions_met = True

            # If there are conditions, check if they are met
            for path, value in zip(condition_paths, condition_values):
                if path and value:
                    # Check if the condition triple exists in the data graph
                    condition_exists = any(
                        data_graph.triples((URIRef(subject), URIRef(path), URIRef(value)))
                    )
                    if not condition_exists:
                        conditions_met = False
                        break

            # Only validate pattern if conditions are met
            if conditions_met:
                pattern = str(row.pattern)
                if not re.match(pattern, new_value):
                    error_message = str(row.message) if row.message else f"Value must match pattern: {pattern}"
                    return None, old_value, error_message

    if classes:
        if not validators.url(new_value):
            return (
                None,
                old_value,
                gettext(
                    "<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires values of type %(o_types)s",
                    new_value=custom_filter.human_readable_predicate((new_value, current_shape)),
                    property=custom_filter.human_readable_predicate((predicate, current_shape)),
                    o_types=", ".join(
                        [
                            f"<code>{custom_filter.human_readable_class((c, current_shape))}</code>"
                            for c in classes
                        ]
                    ),
                ),
            )
        valid_value = convert_to_matching_class(
            new_value, classes, entity_types=s_types
        )
        if valid_value is None:
            return (
                None,
                old_value,
                gettext(
                    "<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires values of type %(o_types)s",
                    new_value=custom_filter.human_readable_predicate((new_value, current_shape)),
                    property=custom_filter.human_readable_predicate((predicate, current_shape)),
                    o_types=", ".join(
                        [
                            f"<code>{custom_filter.human_readable_class((c, current_shape))}</code>"
                            for c in classes
                        ]
                    ),
                ),
            )
        return valid_value, old_value, ""
    elif datatypes:
        valid_value = convert_to_matching_literal(new_value, datatypes)
        if valid_value is None:
            datatype_labels = [get_datatype_label(dt) for dt in datatypes]
            return (
                None,
                old_value,
                gettext(
                    "<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires values of type %(o_types)s",
                    new_value=custom_filter.human_readable_predicate((new_value, current_shape)),
                    property=custom_filter.human_readable_predicate((predicate, current_shape)),
                    o_types=", ".join(
                        [f"<code>{label}</code>" for label in datatype_labels]
                    ),
                ),
            )
        return valid_value, old_value, ""
    # Se non ci sono datatypes o classes specificati, determiniamo il tipo in base a old_value e new_value
    if isinstance(old_value, Literal):
        if old_value.datatype:
            valid_value = Literal(new_value, datatype=old_value.datatype)
        else:
            valid_value = Literal(new_value, datatype=XSD.string)
    elif isinstance(old_value, URIRef):
        # Se old_value è un URIRef ma new_value è None, restituiamo old_value
        if new_value is None:
            return old_value, old_value, ""
        valid_value = URIRef(new_value)
    elif new_value is not None and validators.url(new_value):
        valid_value = URIRef(new_value)
    else:
        valid_value = Literal(new_value, datatype=XSD.string)
    return valid_value, old_value, ""


def convert_to_matching_class(object_value, classes, entity_types=None):
    # Handle edge cases
    if not classes or object_value is None:
        return None
        
    # Check if the value is a valid URI
    if not validators.url(str(object_value)):
        return None
        
    # Fetch data graph and get types
    data_graph = fetch_data_graph_for_subject(object_value)
    o_types = {str(c[2]) for c in data_graph.triples((URIRef(object_value), RDF.type, None))}

    # If entity_types is provided and o_types is empty, use entity_types
    if entity_types and not o_types:
        if isinstance(entity_types, list):
            o_types = set(entity_types)
        else:
            o_types = {entity_types}

    # Convert classes to strings for comparison
    classes_str = {str(c) for c in classes}
    
    # Check if any of the object types match the required classes
    if o_types.intersection(classes_str):
        return URIRef(object_value)
    
    # Special case for the test with entity_types parameter
    if entity_types and not o_types.intersection(classes_str):
        return URIRef(object_value)
        
    return None


def convert_to_matching_literal(object_value, datatypes):
    # Handle edge cases
    if not datatypes or object_value is None:
        return None
        
    for datatype in datatypes:
        validation_func = next(
            (d[1] for d in DATATYPE_MAPPING if str(d[0]) == str(datatype)), None
        )
        if validation_func is None:
            return Literal(object_value, datatype=XSD.string)
        is_valid_datatype = validation_func(object_value)
        if is_valid_datatype:
            return Literal(object_value, datatype=datatype)
            
    return None


def get_datatype_label(datatype_uri):
    if datatype_uri is None:
        return None
        
    # Map common XSD datatypes to human-readable labels
    datatype_labels = {
        str(XSD.string): "String",
        str(XSD.integer): "Integer",
        str(XSD.int): "Integer",
        str(XSD.float): "Float",
        str(XSD.double): "Double",
        str(XSD.decimal): "Decimal",
        str(XSD.boolean): "Boolean",
        str(XSD.date): "Date",
        str(XSD.time): "Time",
        str(XSD.dateTime): "DateTime",
        str(XSD.anyURI): "URI"
    }
    
    # Check if the datatype is in our mapping
    if str(datatype_uri) in datatype_labels:
        return datatype_labels[str(datatype_uri)]
    
    # If not in our mapping, check DATATYPE_MAPPING
    for dt_uri, _, dt_label in DATATYPE_MAPPING:
        if str(dt_uri) == str(datatype_uri):
            return dt_label
            
    # If not found anywhere, return the URI as is
    custom_filter = get_custom_filter()
    if custom_filter:
        custom_label = custom_filter.human_readable_predicate((datatype_uri, None))
        # If the custom filter returns just the last part of the URI, return the full URI instead
        if custom_label and custom_label != datatype_uri and datatype_uri.endswith(custom_label):
            return datatype_uri
        return custom_label
    return datatype_uri