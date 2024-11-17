def get_sortable_properties(entity_type: str, display_rules, form_fields_cache) -> list:
    """
    Ottiene le proprietà ordinabili dalle regole di visualizzazione per un tipo di entità.
    Inferisce il tipo di ordinamento dal form_fields_cache.
    
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
            sort_props = []
            for sort_config in rule['sortableBy']:
                prop = sort_config.copy()
                
                # Trova la displayProperty corrispondente per ottenere il displayName
                for display_prop in rule['displayProperties']:
                    if display_prop['property'] == prop['property']:
                        if 'displayRules' in display_prop:
                            prop['displayName'] = display_prop['displayRules'][0]['displayName']
                        else:
                            prop['displayName'] = display_prop.get('displayName', prop['property'])
                        break
                
                # Determina il tipo di ordinamento dalle form fields
                if form_fields_cache and entity_type in form_fields_cache:
                    entity_fields = form_fields_cache[entity_type]
                    if prop['property'] in entity_fields:
                        field_info = entity_fields[prop['property']][0]  # Prendi il primo field definition
                        
                        # Se c'è una shape, è una referenza a un'entità (ordina per label)
                        if field_info.get('nodeShape'):
                            prop['sortType'] = 'string'
                        # Altrimenti guarda i datatypes
                        elif field_info.get('datatypes'):
                            datatype = str(field_info['datatypes'][0]).lower()
                            if any(t in datatype for t in ['date', 'time']):
                                prop['sortType'] = 'date'
                            elif any(t in datatype for t in ['int', 'float', 'decimal', 'double', 'number']):
                                prop['sortType'] = 'number'
                            else:
                                prop['sortType'] = 'string'
                        else:
                            prop['sortType'] = 'string'
                
                sort_props.append(prop)
                
            return sort_props
            
    return []

def build_sort_clause(sort_property: str, entity_type: str, display_rules) -> str:
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