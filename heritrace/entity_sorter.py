def get_sortable_properties(entity_type: str) -> list:
    from heritrace.app import display_rules
    """
    Ottiene le proprietà ordinabili dalle regole di visualizzazione per un tipo di entità.
    
    Args:
        entity_type: L'URI del tipo di entità
    
    Returns:
        Lista di dizionari con le informazioni di ordinamento
    """
    if not display_rules:
        return []
        
    for rule in display_rules:
        if rule['class'] == entity_type and 'sortableBy' in rule:
            # Aggiungiamo displayName ottenuto dalla proprietà nella classe
            sort_props = rule['sortableBy']
            for prop in sort_props:
                for display_prop in rule['displayProperties']:
                    if display_prop['property'] == prop['property']:
                        if 'displayRules' in display_prop:
                            prop['displayName'] = display_prop['displayRules'][0]['displayName']
                        else:
                            prop['displayName'] = display_prop.get('displayName', prop['property'])
                        break
            return sort_props
            
    return []

def build_sort_clause(sort_property: str, entity_type: str) -> str:
    from heritrace.app import display_rules
    """
    Costruisce la clausola di ordinamento SPARQL in base alla configurazione sortableBy.
    
    Args:
        sort_property: La proprietà su cui ordinare
        entity_type: Il tipo di entità
        
    Returns:
        Clausola SPARQL per l'ordinamento o stringa vuota
    """
    if not display_rules or not sort_property:
        return ""
        
    # Trova la configurazione di ordinamento
    sort_config = None
    for rule in display_rules:
        if rule['class'] == entity_type and 'sortableBy' in rule:
            sort_config = next(
                (s for s in rule['sortableBy'] if s['property'] == sort_property), 
                None
            )
            break
    
    if not sort_config:
        return ""
        
    # Se c'è una shape, indica che è una proprietà che referenzia un'entità
    if 'shape' in sort_config:
        return f"""
            OPTIONAL {{
                ?subject <{sort_property}> ?intermediateNode .
                OPTIONAL {{ ?intermediateNode ?labelPred ?sortValue 
                    FILTER(?labelPred IN (
                        <http://www.w3.org/2000/01/rdf-schema#label>,
                        <http://purl.org/dc/terms/title>,
                        <http://xmlns.com/foaf/0.1/name>
                    ))
                }}
                BIND(COALESCE(?sortValue, STR(?intermediateNode)) AS ?sortValue)
            }}
        """
    
    # Per proprietà dirette
    return f"OPTIONAL {{ ?subject <{sort_property}> ?sortValue }}"