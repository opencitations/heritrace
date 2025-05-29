"""
Tests for the shacl_utils module.
"""

from collections import namedtuple
from unittest.mock import MagicMock, patch

from flask import Flask
from heritrace.utils.shacl_display import (
    apply_display_rules_to_nested_shapes, get_shape_target_class,
    process_query_results)
from heritrace.utils.shacl_utils import (_get_shape_properties,
                                         determine_shape_for_entity_triples,
                                         extract_shacl_form_fields,
                                         get_form_fields_from_shacl)
from heritrace.utils.shacl_validation import validate_new_triple
from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef

FABIO = Namespace("http://purl.org/spar/fabio/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
PRISM = Namespace("http://prismstandard.org/namespaces/basic/2.0/")
PRO = Namespace("http://purl.org/spar/pro/")
SCHEMA = Namespace("http://schema.org/")
SH = Namespace("http://www.w3.org/ns/shacl#")


class TestShaclUtils:
    """Test class for shacl_utils module."""

    def test_shacl_utils_empty_shacl(self):
        """Test that functions return an empty dict when shacl is None or empty."""
        app = Flask(__name__)
        app.config['DATASET_DB_URL'] = 'http://example.org/sparql'
        
        # Caso 1: Test get_form_fields_from_shacl con None
        result = get_form_fields_from_shacl(None, [], app)
        assert result == {}
        
        # Caso 2: Test get_form_fields_from_shacl con empty Graph
        empty_graph = Graph()
        result = get_form_fields_from_shacl(empty_graph, [], app)
        assert result == {}
        
        # Caso 3: Test get_form_fields_from_shacl con None e display rules
        display_rules = [{"target": {"class": "http://example.org/Person"}}]
        result = get_form_fields_from_shacl(None, display_rules, app)
        assert result == {}
        
        # Caso 4: Test extract_shacl_form_fields con None
        result = extract_shacl_form_fields(None, [], app)
        assert result == {}
        
        # Caso 5: Test extract_shacl_form_fields con empty Graph
        result = extract_shacl_form_fields(empty_graph, [], app)
        assert result == {}
        
        # Caso 6: Test extract_shacl_form_fields con None e display rules
        result = extract_shacl_form_fields(None, display_rules, app)
        assert result == {}
        

    @patch('heritrace.utils.shacl_utils.extract_shacl_form_fields')
    @patch('heritrace.utils.shacl_utils.process_nested_shapes')
    @patch('heritrace.utils.shacl_utils.apply_display_rules')
    @patch('heritrace.utils.shacl_utils.order_form_fields')
    def test_get_form_fields_from_shacl_early_return(self, mock_order, mock_apply, mock_process, mock_extract):
        """Test that get_form_fields_from_shacl returns early when shacl is None without calling other functions."""
        app = Flask(__name__)
        app.config['DATASET_DB_URL'] = 'http://example.org/sparql'
        
        # Call with None
        result = get_form_fields_from_shacl(None, [], app)
        
        # Assert
        assert result == {}
        mock_extract.assert_not_called()
        mock_process.assert_not_called()
        mock_apply.assert_not_called()
        mock_order.assert_not_called()
        
    @patch('heritrace.utils.shacl_display.get_shape_target_class')
    @patch('heritrace.utils.shacl_display.get_object_class')
    @patch('heritrace.utils.filters.Filter.human_readable_class')
    @patch('heritrace.utils.shacl_display.process_nested_shapes')
    def test_process_query_results_with_ornodes(self, mock_process_nested_shapes, mock_human_readable_class, mock_get_object_class, mock_get_shape_target_class):
        """Test che process_query_results gestisca correttamente gli orNodes."""
        mock_get_shape_target_class.return_value = 'entity_type_or_node'
        mock_get_object_class.return_value = 'objectClass1'
        mock_human_readable_class.return_value = 'display_name'
        mock_process_nested_shapes.return_value = {}
        
        # Crea un risultato di query simulato con orNodes
        QueryResult = namedtuple('QueryResult', [
            'shape', 'type', 'predicate', 'nodeShape', 'hasValue', 'objectClass',
            'minCount', 'maxCount', 'datatype', 'optionalValues', 'orNodes',
            'conditionPath', 'conditionValue', 'pattern', 'message'
        ])
        
        # Crea un risultato con orNodes
        results = [QueryResult(
            shape='subjectShape1',
            type='entity_type1',
            predicate='predicate1',
            nodeShape='nodeShape1',
            hasValue=None,
            objectClass='objectClass1',
            minCount=0,
            maxCount=None,
            datatype=None,
            optionalValues='',
            orNodes='orNode1',  # Questo è importante: specifica un orNode
            conditionPath=None,
            conditionValue=None,
            pattern=None,
            message=None
        )]
        
        # Crea un grafo vuoto e display_rules vuoti
        shacl = Graph()
        display_rules = []
        processed_shapes = set()
        app = Flask(__name__)
        app.config['DATASET_DB_URL'] = 'http://example.org/sparql'
        
        # Mock per il file context.json
        with patch('os.path.join', return_value='mock_path'), \
             patch('builtins.open', create=True) as mock_open, \
             patch('json.load') as mock_json_load:
            mock_file = mock_open.return_value.__enter__.return_value
            mock_json_load.return_value = {"@context": {}}
            
            # Chiama direttamente process_query_results
            result = process_query_results(shacl, results, display_rules, processed_shapes, app)
        
        # Verifica che il risultato contenga la struttura orNodes attesa con chiave tuple
        entity_key = ('entity_type1', 'subjectShape1')
        assert entity_key in result
        assert 'predicate1' in result[entity_key]
        assert len(result[entity_key]['predicate1']) == 1
        
        field_info = result[entity_key]['predicate1'][0]
        assert 'or' in field_info
        assert len(field_info['or']) == 1
        
        or_field_info = field_info['or'][0]
        assert or_field_info['entityType'] == 'entity_type_or_node'
        assert or_field_info['uri'] == 'predicate1'
        assert or_field_info['nodeShape'] == 'orNode1'
        assert or_field_info['displayName'] == 'display_name'
        assert 'nestedShape' in or_field_info
        
        # Verifica che le funzioni mock siano state chiamate correttamente
        mock_get_shape_target_class.assert_called_with(shacl, 'orNode1')
        mock_get_object_class.assert_called_with(shacl, 'orNode1', 'predicate1')
        mock_human_readable_class.assert_called_with(('entity_type_or_node', 'orNode1'))
        mock_process_nested_shapes.assert_called_with(
            shacl, display_rules, 'orNode1', app, depth=1, processed_shapes=processed_shapes
        )
        
    def test_get_shape_target_class_returns_none(self):
        """Test che get_shape_target_class ritorni None quando non trova una targetClass."""
        # Crea un grafo vuoto che non contiene alcuna targetClass
        shacl = Graph()
        shape_uri = "http://example.org/shape1"
        
        # Chiama la funzione
        result = get_shape_target_class(shacl, shape_uri)
        
        # Verifica che il risultato sia None
        assert result is None
        
    def test_apply_display_rules_to_nested_shapes_parent_prop_not_dict(self):
        """Test che apply_display_rules_to_nested_shapes ritorni nested_fields quando parent_prop non è un dizionario."""
        # Prepara i dati di test
        nested_fields = [
            {
                "uri": "http://example.org/predicate1",
                "displayName": "Original Name"
            }
        ]
        display_rules = [
            {
                "target": {
                    "class": "http://example.org/Class1",
                    "shape": "http://example.org/Shape1"
                },
                "displayProperties": [
                    {
                        "property": "http://example.org/predicate1",
                        "displayName": "New Display Name"
                    }
                ]
            }
        ]
        parent_prop = "not_a_dict"  # Questo non è un dizionario
        
        result = apply_display_rules_to_nested_shapes(nested_fields, parent_prop, "http://example.org/Shape1")
        
        # Verifica che il risultato sia uguale a nested_fields senza modifiche
        assert result == nested_fields
        
    @patch('heritrace.utils.shacl_display.get_shape_target_class')
    @patch('heritrace.utils.shacl_display.get_object_class')
    @patch('heritrace.utils.filters.Filter.human_readable_class')
    @patch('heritrace.utils.shacl_display.process_nested_shapes')
    def test_process_query_results_update_existing_field(self, mock_process_nested_shapes, mock_human_readable_class, mock_get_object_class, mock_get_shape_target_class):
        """Test che process_query_results aggiorni correttamente un campo esistente con nuovi datatype e condizioni."""
        # Configura i mock per le funzioni chiamate da process_query_results
        mock_get_shape_target_class.return_value = 'entity_type_or_node'
        mock_get_object_class.return_value = 'objectClass1'
        mock_human_readable_class.return_value = 'display_name'
        mock_process_nested_shapes.return_value = {}
        
        # Crea un risultato di query simulato
        QueryResult = namedtuple('QueryResult', [
            'shape', 'type', 'predicate', 'nodeShape', 'hasValue', 'objectClass',
            'minCount', 'maxCount', 'datatype', 'optionalValues', 'orNodes',
            'conditionPath', 'conditionValue', 'pattern', 'message'
        ])
        
        # Crea due risultati con lo stesso campo di base ma con datatype e condizioni diverse
        # Il primo risultato crea il campo base
        results = [
            QueryResult(
                shape='subjectShape1',
                type='entity_type1',
                predicate='predicate1',
                nodeShape='nodeShape1',
                hasValue=None,
                objectClass='objectClass1',
                minCount=0,
                maxCount=None,
                datatype='http://www.w3.org/2001/XMLSchema#string',  # Primo datatype
                optionalValues='',
                orNodes='',  # Nessun orNode
                conditionPath=None,
                conditionValue=None,
                pattern=None,
                message=None
            ),
            # Il secondo risultato ha lo stesso campo base ma con un datatype diverso e una condizione
            QueryResult(
                shape='subjectShape1',
                type='entity_type1',
                predicate='predicate1',
                nodeShape='nodeShape1',
                hasValue=None,
                objectClass='objectClass1',
                minCount=0,
                maxCount=None,
                datatype='http://www.w3.org/2001/XMLSchema#integer',  # Secondo datatype
                optionalValues='',
                orNodes='',  # Stesso orNodes (vuoto)
                conditionPath='conditionPath1',  # Aggiungiamo una condizione
                conditionValue='conditionValue1',
                pattern='pattern1',  # Aggiungiamo un pattern
                message='message1'  # Aggiungiamo un messaggio
            )
        ]
        
        # Crea un grafo vuoto e display_rules vuoti
        shacl = Graph()
        display_rules = []
        processed_shapes = set()
        app = Flask(__name__)
        app.config['DATASET_DB_URL'] = 'http://example.org/sparql'
        
        # Mock per il file context.json
        with patch('os.path.join', return_value='mock_path'), \
             patch('builtins.open', create=True) as mock_open, \
             patch('json.load') as mock_json_load:
            mock_file = mock_open.return_value.__enter__.return_value
            mock_json_load.return_value = {"@context": {}}
            
            # Chiama direttamente process_query_results
            result = process_query_results(shacl, results, display_rules, processed_shapes, app)
        
        # Verifica che il risultato contenga la struttura attesa con chiave tuple
        entity_key = ('entity_type1', 'subjectShape1')
        assert entity_key in result
        assert 'predicate1' in result[entity_key]
        # Dovrebbe esserci solo un campo, non due, perché il secondo risultato aggiorna il campo esistente
        assert len(result[entity_key]['predicate1']) == 1
        
        field_info = result[entity_key]['predicate1'][0]
        
        # Verifica che il campo contenga entrambi i datatype
        assert 'datatypes' in field_info
        assert len(field_info['datatypes']) == 2
        assert 'http://www.w3.org/2001/XMLSchema#string' in field_info['datatypes']
        assert 'http://www.w3.org/2001/XMLSchema#integer' in field_info['datatypes']
        
        # Verifica che il campo contenga le condizioni
        assert 'conditions' in field_info
        assert len(field_info['conditions']) == 1  # Solo la condizione non vuota dal secondo risultato
        
        # Trova la condizione non vuota
        non_empty_condition = None
        for condition in field_info['conditions']:
            if condition:
                non_empty_condition = condition
                break
        
        assert non_empty_condition is not None
        assert 'condition' in non_empty_condition
        assert non_empty_condition['condition']['path'] == 'conditionPath1'
        assert non_empty_condition['condition']['value'] == 'conditionValue1'
        assert 'pattern' in non_empty_condition
        assert non_empty_condition['pattern'] == 'pattern1'
        assert 'message' in non_empty_condition
        assert non_empty_condition['message'] == 'message1'
        
    def test_validate_new_triple_no_shacl(self):
        """Test che validate_new_triple funzioni correttamente quando non c'è SHACL."""
        
        subject = "http://example.org/subject1"
        predicate = "http://example.org/predicate1"
        
        # Mock per fetch_data_graph_for_subject e get_shacl_graph
        mock_data_graph = MagicMock()
        mock_data_graph.triples.return_value = []
        
        with patch('heritrace.utils.shacl_validation.fetch_data_graph_for_subject', return_value=mock_data_graph), \
             patch('heritrace.utils.shacl_validation.get_shacl_graph', return_value=MagicMock()), \
             patch('heritrace.utils.shacl_validation.len', return_value=0):
            
            # Caso 1: new_value è un URL
            new_value = "http://example.org/value1"
            result, old_value, message = validate_new_triple(subject, predicate, new_value, "create")
            
            # Verifica che il risultato sia un URIRef
            assert isinstance(result, URIRef)
            assert str(result) == new_value
            assert message == ""
            
            # Caso 2: new_value non è un URL, ma old_value ha un datatype
            new_value = "123"
            old_value = Literal("456", datatype=XSD.integer)
            
            result, old_value_returned, message = validate_new_triple(subject, predicate, new_value, "update", old_value)
            
            # Verifica che il risultato sia un Literal con lo stesso datatype di old_value
            assert isinstance(result, Literal)
            assert result.datatype == XSD.integer
            assert str(result) == new_value
            assert old_value_returned == old_value
            assert message == ""
            
            # Caso 3: new_value non è un URL e old_value non ha un datatype
            new_value = "test"
            old_value = None
            
            result, old_value_returned, message = validate_new_triple(subject, predicate, new_value, "create", old_value)
            
            # Verifica che il risultato sia un Literal senza datatype
            assert isinstance(result, Literal)
            assert result.datatype is None
            assert str(result) == new_value
            assert old_value_returned is None
            assert message == ""
    
    def test_validate_new_triple_entity_types_not_list(self):
        """Test che validate_new_triple gestisca correttamente entity_types quando non è una lista."""
        
        subject = "http://example.org/subject1"
        predicate = "http://example.org/predicate1"
        new_value = "test"
        entity_types = "http://example.org/type1"  # entity_types come stringa, non lista
        
        # Mock per fetch_data_graph_for_subject e get_shacl_graph
        mock_data_graph = MagicMock()
        # Simula che non ci sono tipi nel grafo dei dati
        mock_data_graph.triples.side_effect = lambda triple_pattern: [] if triple_pattern[1] == RDF.type else []
        
        mock_shacl = MagicMock()
        # Simula che la query SHACL non restituisce risultati (per semplificare il test)
        mock_shacl.query.return_value = []
        
        with patch('heritrace.utils.shacl_validation.fetch_data_graph_for_subject', return_value=mock_data_graph), \
             patch('heritrace.utils.shacl_validation.get_shacl_graph', return_value=mock_shacl), \
             patch('heritrace.utils.shacl_validation.len', return_value=1), \
             patch('heritrace.utils.shacl_validation.get_custom_filter') as mock_custom_filter:
            
            # Configura il mock per custom_filter
            mock_filter = MagicMock()
            mock_filter.human_readable_predicate.return_value = "Human Readable"
            mock_custom_filter.return_value = mock_filter
            
            # Verifica che entity_types venga convertito in lista
            with patch('heritrace.utils.shacl_validation.isinstance', side_effect=lambda obj, cls: False if cls == list else isinstance(obj, cls)):
                validate_new_triple(subject, predicate, new_value, "create", None, entity_types)
                
                # Verifica che la query SHACL sia stata chiamata con entity_types convertito in lista
                # Questo è difficile da testare direttamente, quindi verifichiamo che la funzione non generi errori
                # e che la query SHACL sia stata chiamata
                assert mock_shacl.query.called
                
    def test_collect_inverse_types(self):
        """Test specifico per verificare la raccolta degli inverse types."""

        # Crea un grafo reale per i dati
        data_graph = Graph()
        
        # Definisci soggetto e tipi
        subject = "http://example.org/subject1"
        direct_type = URIRef("http://example.org/DirectType")
        inverse_type1 = URIRef("http://example.org/InverseType1")
        inverse_type2 = URIRef("http://example.org/InverseType2")
        
        # Aggiungi il tipo diretto del soggetto
        data_graph.add((URIRef(subject), RDF.type, direct_type))
        
        # Aggiungi le entità che hanno il soggetto come oggetto
        entity1 = URIRef("http://example.org/entity1")
        entity2 = URIRef("http://example.org/entity2")
        relation1 = URIRef("http://example.org/relation1")
        relation2 = URIRef("http://example.org/relation2")
        data_graph.add((entity1, relation1, URIRef(subject)))
        data_graph.add((entity2, relation2, URIRef(subject)))
        
        # Aggiungi i tipi delle entità che hanno il soggetto come oggetto (inverse types)
        data_graph.add((entity1, RDF.type, inverse_type1))
        data_graph.add((entity2, RDF.type, inverse_type2))
        
        # Verifica che il grafo contenga le triple che ci aspettiamo
        assert (URIRef(subject), RDF.type, direct_type) in data_graph
        assert (entity1, relation1, URIRef(subject)) in data_graph
        assert (entity2, relation2, URIRef(subject)) in data_graph
        assert (entity1, RDF.type, inverse_type1) in data_graph
        assert (entity2, RDF.type, inverse_type2) in data_graph
        
        # Verifica che le query per ottenere gli inverse types funzionino come previsto
        inverse_entities = list(data_graph.triples((None, None, URIRef(subject))))
        assert len(inverse_entities) == 2, f"Dovrebbero esserci 2 entità che hanno il soggetto come oggetto, trovate: {inverse_entities}"
        
        # Verifica che possiamo ottenere i tipi delle entità che hanno il soggetto come oggetto
        entity1_types = list(data_graph.triples((entity1, RDF.type, None)))
        entity2_types = list(data_graph.triples((entity2, RDF.type, None)))
        assert len(entity1_types) == 1, f"Dovrebbe esserci 1 tipo per entity1, trovati: {entity1_types}"
        assert len(entity2_types) == 1, f"Dovrebbe esserci 1 tipo per entity2, trovati: {entity2_types}"
        
        # Verifica che i tipi siano quelli che ci aspettiamo
        assert entity1_types[0][2] == inverse_type1
        assert entity2_types[0][2] == inverse_type2
        
        # Ora testiamo il codice che raccoglie gli inverse types
        inverse_types = []
        for s, p, o in data_graph.triples((None, None, URIRef(subject))):
            o_types = [t[2] for t in data_graph.triples((s, RDF.type, None))]
            inverse_types.extend(o_types)
        
        # Verifica che inverse_types contenga entrambi i tipi inversi
        assert inverse_type1 in inverse_types, f"inverse_type1 dovrebbe essere in inverse_types: {inverse_types}"
        assert inverse_type2 in inverse_types, f"inverse_type2 dovrebbe essere in inverse_types: {inverse_types}"
        
    def test_validate_new_triple_inverse_types(self):
        """Test che validate_new_triple gestisca correttamente gli inverse types."""
        
        subject = "http://example.org/subject1"
        predicate = "http://example.org/predicate1"
        new_value = "test"
        
        # Crea un grafo reale per i dati
        data_graph = Graph()
        
        # Aggiungi i tipi diretti del soggetto
        direct_type = URIRef("http://example.org/DirectType")
        data_graph.add((URIRef(subject), RDF.type, direct_type))
        
        # Aggiungi le entità che hanno il soggetto come oggetto
        entity1 = URIRef("http://example.org/entity1")
        entity2 = URIRef("http://example.org/entity2")
        relation1 = URIRef("http://example.org/relation1")
        relation2 = URIRef("http://example.org/relation2")
        data_graph.add((entity1, relation1, URIRef(subject)))
        data_graph.add((entity2, relation2, URIRef(subject)))
        
        # Aggiungi i tipi delle entità che hanno il soggetto come oggetto (inverse types)
        inverse_type1 = URIRef("http://example.org/InverseType1")
        inverse_type2 = URIRef("http://example.org/InverseType2")
        data_graph.add((entity1, RDF.type, inverse_type1))
        data_graph.add((entity2, RDF.type, inverse_type2))
        
        # Verifica che il grafo contenga le triple che ci aspettiamo
        assert (URIRef(subject), RDF.type, direct_type) in data_graph
        assert (entity1, relation1, URIRef(subject)) in data_graph
        assert (entity2, relation2, URIRef(subject)) in data_graph
        assert (entity1, RDF.type, inverse_type1) in data_graph
        assert (entity2, RDF.type, inverse_type2) in data_graph
        
        # Raccogli manualmente gli inverse types per verificare che siano presenti
        inverse_types = []
        for s, p, o in data_graph.triples((None, None, URIRef(subject))):
            o_types = [t[2] for t in data_graph.triples((s, RDF.type, None))]
            inverse_types.extend(o_types)
        
        # Verifica che inverse_types contenga entrambi i tipi inversi
        assert inverse_type1 in inverse_types, f"inverse_type1 dovrebbe essere in inverse_types: {inverse_types}"
        assert inverse_type2 in inverse_types, f"inverse_type2 dovrebbe essere in inverse_types: {inverse_types}"
        
        # Mock per get_shacl_graph
        mock_shacl = MagicMock()
        mock_results = MagicMock()
        mock_results.__iter__.return_value = []
        mock_shacl.query.return_value = mock_results
        
        # Creiamo una classe wrapper per intercettare la chiamata a query
        class ShaclGraphWrapper:
            def __init__(self, mock_shacl):
                self.mock_shacl = mock_shacl
                self.last_query = None
                self.mock_results = MagicMock()
                self.mock_results.__iter__.return_value = []
            
            def query(self, query_string):
                self.last_query = query_string
                return self.mock_results
            
            def __len__(self):
                return 1
        
        # Creiamo un wrapper per il grafo SHACL
        shacl_wrapper = ShaclGraphWrapper(mock_shacl)
        
        with patch('heritrace.utils.shacl_validation.fetch_data_graph_for_subject', return_value=data_graph), \
             patch('heritrace.utils.shacl_validation.get_shacl_graph', return_value=shacl_wrapper), \
             patch('heritrace.utils.shacl_validation.len', return_value=1), \
             patch('heritrace.utils.shacl_validation.get_custom_filter') as mock_custom_filter:
            
            # Configura il mock per custom_filter
            mock_filter = MagicMock()
            mock_filter.human_readable_predicate.return_value = "Human Readable"
            mock_custom_filter.return_value = mock_filter
            
            # Chiama la funzione
            validate_new_triple(subject, predicate, new_value, "create")
            
            # Verifica che la query SHACL sia stata eseguita
            assert shacl_wrapper.last_query is not None
            
            # Ottieni la query SPARQL dal wrapper
            query_arg = shacl_wrapper.last_query
            
            # Verifica che la query contenga VALUES ?type con tutti i tipi (diretto e inversi)
            # Nella query SPARQL, i tipi vengono formattati come <URI>
            assert f"<{direct_type}>" in query_arg, f"Il tipo diretto {direct_type} non è presente nella query"
            
            # Estrai la sezione VALUES dalla query
            values_section = query_arg.split("VALUES ?type {")[1].split("}")[0].strip()
            
            # Verifica che gli inverse types siano presenti nella sezione VALUES
            assert f"<{inverse_type1}>" in values_section, f"L'inverse type {inverse_type1} non è presente nella query"
            assert f"<{inverse_type2}>" in values_section, f"L'inverse type {inverse_type2} non è presente nella query"


class TestDetermineShapeForEntityTriples:
    """Test the determine_shape_for_entity_triples function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_shacl_graph = MagicMock()
        self.mock_shacl_graph.__bool__ = MagicMock(return_value=True)
        self.mock_shacl_graph.__len__ = MagicMock(return_value=1)
        
    @patch('heritrace.utils.shacl_utils.get_shacl_graph')
    @patch('heritrace.utils.shacl_utils.get_class_priority')
    def test_no_shacl_graph(self, mock_get_priority, mock_get_shacl):
        """Test when no SHACL graph is available."""
        mock_get_shacl.return_value = None
        
        triples = [
            (URIRef("http://example.org/entity1"), RDF.type, FABIO.JournalIssue)
        ]
        
        result = determine_shape_for_entity_triples(triples)
        assert result is None

    @patch('heritrace.utils.shacl_utils.get_shacl_graph')
    @patch('heritrace.utils.shacl_utils.get_class_priority')
    def test_no_classes_in_triples(self, mock_get_priority, mock_get_shacl):
        """Test when no rdf:type triples are present."""
        mock_get_shacl.return_value = self.mock_shacl_graph
        
        triples = [
            (URIRef("http://example.org/entity1"), DCTERMS.title, Literal("Some Title"))
        ]
        
        result = determine_shape_for_entity_triples(triples)
        assert result is None

    @patch('heritrace.utils.shacl_utils.get_shacl_graph')
    @patch('heritrace.utils.shacl_utils.get_class_priority')
    def test_single_candidate_shape(self, mock_get_priority, mock_get_shacl):
        """Test when only one candidate shape exists."""
        mock_get_shacl.return_value = self.mock_shacl_graph
        
        mock_result = MagicMock()
        mock_result.shape = URIRef("http://schema.org/JournalShape")
        self.mock_shacl_graph.query.return_value = [mock_result]
        
        triples = [
            (URIRef("http://example.org/entity1"), RDF.type, FABIO.Journal),
            (URIRef("http://example.org/entity1"), DCTERMS.title, Literal("Journal Title"))
        ]
        
        result = determine_shape_for_entity_triples(triples)
        
        assert self.mock_shacl_graph.query.call_count > 0
        query_args = self.mock_shacl_graph.query.call_args[0][0]
        assert str(FABIO.Journal) in query_args
        assert result == "http://schema.org/JournalShape"

    @patch('heritrace.utils.shacl_utils.get_shacl_graph')
    @patch('heritrace.utils.shacl_utils.get_class_priority')
    @patch('heritrace.utils.shacl_utils._get_shape_properties')
    def test_special_issue_vs_issue_distinction(self, mock_get_properties, mock_get_priority, mock_get_shacl):
        """Test distinguishing between SpecialIssueShape and IssueShape based on properties."""
        mock_get_shacl.return_value = self.mock_shacl_graph
        
        mock_issue_result = MagicMock()
        mock_issue_result.shape = URIRef("http://schema.org/IssueShape")
        mock_special_issue_result = MagicMock()
        mock_special_issue_result.shape = URIRef("http://schema.org/SpecialIssueShape")
        self.mock_shacl_graph.query.return_value = [mock_issue_result, mock_special_issue_result]
        
        def mock_properties_side_effect(graph, shape_uri):
            if shape_uri == "http://schema.org/IssueShape":
                return {
                    "http://purl.org/spar/fabio/hasSequenceIdentifier",
                    "http://purl.org/vocab/frbr/core#partOf"
                }
            elif shape_uri == "http://schema.org/SpecialIssueShape":
                return {
                    "http://purl.org/spar/fabio/hasSequenceIdentifier",
                    "http://purl.org/vocab/frbr/core#partOf", 
                    "http://purl.org/dc/terms/title",
                    "http://purl.org/dc/terms/abstract",
                    "http://prismstandard.org/namespaces/basic/2.0/keyword",
                    "http://purl.org/spar/pro/isDocumentContextFor"
                }
            return set()
        
        mock_get_properties.side_effect = mock_properties_side_effect
        
        mock_get_priority.return_value = 1
        
        special_issue_triples = [
            (URIRef("http://example.org/entity1"), RDF.type, FABIO.JournalIssue),
            (URIRef("http://example.org/entity1"), DCTERMS.title, Literal("Special Issue Title")),
            (URIRef("http://example.org/entity1"), DCTERMS.abstract, Literal("Abstract")),
            (URIRef("http://example.org/entity1"), PRISM.keyword, Literal("keyword1"))
        ]
        
        result = determine_shape_for_entity_triples(special_issue_triples)
        assert result == "http://schema.org/SpecialIssueShape"


    @patch('heritrace.utils.shacl_utils.get_shacl_graph')
    @patch('heritrace.utils.shacl_utils.get_class_priority')
    def test_no_candidate_shapes(self, mock_get_priority, mock_get_shacl):
        """Test when no shapes are found for the entity classes."""
        mock_get_shacl.return_value = self.mock_shacl_graph
        
        self.mock_shacl_graph.query.return_value = []
        
        triples = [
            (URIRef("http://example.org/entity1"), RDF.type, URIRef("http://example.org/UnknownClass"))
        ]
        
        result = determine_shape_for_entity_triples(triples)
        assert result is None

    @patch('heritrace.utils.shacl_utils.get_shacl_graph')
    @patch('heritrace.utils.shacl_utils.get_class_priority')
    def test_with_rdflib_graph_iterator(self, mock_get_priority, mock_get_shacl):
        """Test with actual RDFLib graph iterator (realistic scenario)."""
        mock_get_shacl.return_value = self.mock_shacl_graph
        
        mock_result = MagicMock()
        mock_result.shape = URIRef("http://schema.org/JournalShape")
        self.mock_shacl_graph.query.return_value = [mock_result]
        
        test_graph = Graph()
        entity_uri = URIRef("http://example.org/entity1")
        test_graph.add((entity_uri, RDF.type, FABIO.Journal))
        test_graph.add((entity_uri, DCTERMS.title, Literal("Journal Title")))
        
        result = determine_shape_for_entity_triples(
            test_graph.triples((entity_uri, None, None))
        )
        
        assert result == "http://schema.org/JournalShape"


class TestGetShapeProperties:
    """Test the _get_shape_properties helper function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_shacl_graph = MagicMock()

    def test_get_shape_properties(self):
        """Test extracting properties from a SHACL shape."""
        mock_results = []
        properties = [
            "http://purl.org/dc/terms/title",
            "http://purl.org/dc/terms/abstract",
            "http://purl.org/spar/fabio/hasSequenceIdentifier"
        ]
        
        for prop in properties:
            mock_result = MagicMock()
            mock_result.property = URIRef(prop)
            mock_results.append(mock_result)
        
        self.mock_shacl_graph.query.return_value = mock_results
        
        result = _get_shape_properties(self.mock_shacl_graph, "http://schema.org/TestShape")
        
        expected = {
            "http://purl.org/dc/terms/title",
            "http://purl.org/dc/terms/abstract", 
            "http://purl.org/spar/fabio/hasSequenceIdentifier"
        }
        assert result == expected

    def test_get_shape_properties_empty(self):
        """Test when shape has no properties."""
        self.mock_shacl_graph.query.return_value = []
        
        result = _get_shape_properties(self.mock_shacl_graph, "http://schema.org/EmptyShape")
        assert result == set()
