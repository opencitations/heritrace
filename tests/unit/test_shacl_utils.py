"""
Tests for the shacl_utils module.
"""

from collections import namedtuple
from unittest.mock import MagicMock, patch

from flask import Flask
from heritrace.utils.shacl_display import (
    apply_display_rules_to_nested_shapes, get_shape_target_class,
    process_query_results)
from heritrace.utils.shacl_utils import (_find_entity_position_in_order_map,
                                         _get_shape_properties,
                                         determine_shape_for_entity_triples,
                                         extract_shacl_form_fields,
                                         get_entity_position_in_sequence,
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


class TestFindEntityPositionInOrderMap:
    """Test the _find_entity_position_in_order_map helper function."""

    def test_empty_order_map(self):
        """Test with empty order map."""
        order_map = {}
        result = _find_entity_position_in_order_map("http://example.org/entity1", order_map)
        assert result is None

    def test_single_element_chain(self):
        """Test with a single element chain."""
        order_map = {"http://example.org/entity1": None}
        
        # Entity exists in chain
        result = _find_entity_position_in_order_map("http://example.org/entity1", order_map)
        assert result == 1
        
        # Entity doesn't exist
        result = _find_entity_position_in_order_map("http://example.org/entity2", order_map)
        assert result is None

    def test_simple_chain(self):
        """Test with a simple linear chain of 3 elements."""
        order_map = {
            "http://example.org/entity1": "http://example.org/entity2",
            "http://example.org/entity2": "http://example.org/entity3",
            "http://example.org/entity3": None
        }
        
        # Test each position
        assert _find_entity_position_in_order_map("http://example.org/entity1", order_map) == 1
        assert _find_entity_position_in_order_map("http://example.org/entity2", order_map) == 2
        assert _find_entity_position_in_order_map("http://example.org/entity3", order_map) == 3
        
        # Test non-existent entity
        assert _find_entity_position_in_order_map("http://example.org/entity4", order_map) is None

    def test_multiple_independent_chains(self):
        """Test with multiple independent chains."""
        order_map = {
            # First chain: entity1 -> entity2 -> entity3
            "http://example.org/entity1": "http://example.org/entity2",
            "http://example.org/entity2": "http://example.org/entity3",
            "http://example.org/entity3": None,
            # Second chain: entity4 -> entity5
            "http://example.org/entity4": "http://example.org/entity5",
            "http://example.org/entity5": None
        }
        
        # Test first chain positions
        assert _find_entity_position_in_order_map("http://example.org/entity1", order_map) == 1
        assert _find_entity_position_in_order_map("http://example.org/entity2", order_map) == 2
        assert _find_entity_position_in_order_map("http://example.org/entity3", order_map) == 3
        
        # Test second chain positions
        assert _find_entity_position_in_order_map("http://example.org/entity4", order_map) == 1
        assert _find_entity_position_in_order_map("http://example.org/entity5", order_map) == 2
        
        # Test non-existent entity
        assert _find_entity_position_in_order_map("http://example.org/entity6", order_map) is None

    def test_multiple_single_element_chains(self):
        """Test with multiple single-element chains."""
        order_map = {
            "http://example.org/entity1": None,
            "http://example.org/entity2": None,
            "http://example.org/entity3": None
        }
        
        # Each entity should be at position 1 in its own chain
        assert _find_entity_position_in_order_map("http://example.org/entity1", order_map) == 1
        assert _find_entity_position_in_order_map("http://example.org/entity2", order_map) == 1
        assert _find_entity_position_in_order_map("http://example.org/entity3", order_map) == 1
        
        # Test non-existent entity
        assert _find_entity_position_in_order_map("http://example.org/entity4", order_map) is None

    def test_complex_multiple_chains(self):
        """Test with chains of different lengths."""
        order_map = {
            # Chain 1: single element
            "http://example.org/single": None,
            # Chain 2: two elements
            "http://example.org/first": "http://example.org/second",
            "http://example.org/second": None,
            # Chain 3: four elements
            "http://example.org/alpha": "http://example.org/beta",
            "http://example.org/beta": "http://example.org/gamma",
            "http://example.org/gamma": "http://example.org/delta",
            "http://example.org/delta": None
        }
        
        # Test single element chain
        assert _find_entity_position_in_order_map("http://example.org/single", order_map) == 1
        
        # Test two-element chain
        assert _find_entity_position_in_order_map("http://example.org/first", order_map) == 1
        assert _find_entity_position_in_order_map("http://example.org/second", order_map) == 2
        
        # Test four-element chain
        assert _find_entity_position_in_order_map("http://example.org/alpha", order_map) == 1
        assert _find_entity_position_in_order_map("http://example.org/beta", order_map) == 2
        assert _find_entity_position_in_order_map("http://example.org/gamma", order_map) == 3
        assert _find_entity_position_in_order_map("http://example.org/delta", order_map) == 4

    def test_no_starting_elements(self):
        """Test edge case where there are no valid starting elements (circular reference)."""
        # This represents a circular reference where every element points to another
        # and no element is a valid starting point (no element is missing as a value)
        order_map = {
            "http://example.org/entity1": "http://example.org/entity2",
            "http://example.org/entity2": "http://example.org/entity1"  # circular
        }
        
        # This should return None because there are no valid starting points
        result = _find_entity_position_in_order_map("http://example.org/entity1", order_map)
        assert result is None
        
        result = _find_entity_position_in_order_map("http://example.org/entity2", order_map)
        assert result is None

    def test_broken_chain_with_missing_element(self):
        """Test chain where an intermediate element is missing from the map."""
        order_map = {
            "http://example.org/entity1": "http://example.org/entity2",
            # entity2 is missing from the map keys
            "http://example.org/entity3": None
        }
        
        # entity1 should be found at position 1 (it's a starting element)
        assert _find_entity_position_in_order_map("http://example.org/entity1", order_map) == 1
        
        # entity2 is not in the keys, so it won't be found
        assert _find_entity_position_in_order_map("http://example.org/entity2", order_map) is None
        
        # entity3 should be found at position 1 (it's a separate single-element chain)
        assert _find_entity_position_in_order_map("http://example.org/entity3", order_map) == 1

    def test_realistic_ordered_entities(self):
        """Test with realistic entity URIs that might appear in cultural heritage data."""
        order_map = {
            "http://heritrace.org/entity/chapter1": "http://heritrace.org/entity/chapter2",
            "http://heritrace.org/entity/chapter2": "http://heritrace.org/entity/chapter3",
            "http://heritrace.org/entity/chapter3": "http://heritrace.org/entity/chapter4",
            "http://heritrace.org/entity/chapter4": None,
            # Separate chain for appendices
            "http://heritrace.org/entity/appendixA": "http://heritrace.org/entity/appendixB",
            "http://heritrace.org/entity/appendixB": None
        }
        
        # Test chapter ordering
        assert _find_entity_position_in_order_map("http://heritrace.org/entity/chapter1", order_map) == 1
        assert _find_entity_position_in_order_map("http://heritrace.org/entity/chapter2", order_map) == 2
        assert _find_entity_position_in_order_map("http://heritrace.org/entity/chapter3", order_map) == 3
        assert _find_entity_position_in_order_map("http://heritrace.org/entity/chapter4", order_map) == 4
        
        # Test appendix ordering
        assert _find_entity_position_in_order_map("http://heritrace.org/entity/appendixA", order_map) == 1
        assert _find_entity_position_in_order_map("http://heritrace.org/entity/appendixB", order_map) == 2
        
        # Test non-existent entity
        assert _find_entity_position_in_order_map("http://heritrace.org/entity/chapter5", order_map) is None

    def test_order_map_with_none_values_mixed(self):
        """Test order map with mixed None and string values."""
        order_map = {
            "http://example.org/start1": "http://example.org/middle1",
            "http://example.org/middle1": None,  # End of first chain
            "http://example.org/start2": None,    # Single element chain
            "http://example.org/start3": "http://example.org/middle3",
            "http://example.org/middle3": "http://example.org/end3",
            "http://example.org/end3": None       # End of third chain
        }
        
        # First chain
        assert _find_entity_position_in_order_map("http://example.org/start1", order_map) == 1
        assert _find_entity_position_in_order_map("http://example.org/middle1", order_map) == 2
        
        # Single element chain
        assert _find_entity_position_in_order_map("http://example.org/start2", order_map) == 1
        
        # Third chain
        assert _find_entity_position_in_order_map("http://example.org/start3", order_map) == 1
        assert _find_entity_position_in_order_map("http://example.org/middle3", order_map) == 2
        assert _find_entity_position_in_order_map("http://example.org/end3", order_map) == 3


class TestGetEntityPositionInSequence:
    """Test the get_entity_position_in_sequence function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.entity_uri = "http://example.org/entity1"
        self.subject_uri = "http://example.org/subject1"  
        self.predicate_uri = "http://example.org/hasPart"
        self.order_property = "http://example.org/next"

    @patch('heritrace.utils.shacl_utils.get_sparql')
    def test_with_sparql_query_simple_chain(self, mock_get_sparql):
        """Test with SPARQL query for a simple chain."""
        # Mock SPARQL wrapper
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        # Mock query results - simple chain: entity1 -> entity2 -> entity3
        mock_results = {
            "results": {
                "bindings": [
                    {
                        "orderedEntity": {"value": "http://example.org/entity1"},
                        "nextValue": {"value": "http://example.org/entity2"}
                    },
                    {
                        "orderedEntity": {"value": "http://example.org/entity2"},
                        "nextValue": {"value": "http://example.org/entity3"}
                    },
                    {
                        "orderedEntity": {"value": "http://example.org/entity3"},
                        "nextValue": {"value": "NONE"}
                    }
                ]
            }
        }
        
        mock_sparql.query.return_value.convert.return_value = mock_results
        
        # Test each position
        result = get_entity_position_in_sequence(
            "http://example.org/entity1", self.subject_uri, 
            self.predicate_uri, self.order_property
        )
        assert result == 1
        
        result = get_entity_position_in_sequence(
            "http://example.org/entity2", self.subject_uri, 
            self.predicate_uri, self.order_property
        )
        assert result == 2
        
        result = get_entity_position_in_sequence(
            "http://example.org/entity3", self.subject_uri, 
            self.predicate_uri, self.order_property
        )
        assert result == 3
        
        # Test non-existent entity
        result = get_entity_position_in_sequence(
            "http://example.org/entity4", self.subject_uri, 
            self.predicate_uri, self.order_property
        )
        assert result is None

    @patch('heritrace.utils.shacl_utils.get_sparql')
    def test_with_sparql_query_multiple_chains(self, mock_get_sparql):
        """Test with SPARQL query for multiple independent chains."""
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        # Mock query results - two chains: entity1->entity2 and entity3 (single)
        mock_results = {
            "results": {
                "bindings": [
                    {
                        "orderedEntity": {"value": "http://example.org/entity1"},
                        "nextValue": {"value": "http://example.org/entity2"}
                    },
                    {
                        "orderedEntity": {"value": "http://example.org/entity2"},
                        "nextValue": {"value": "NONE"}
                    },
                    {
                        "orderedEntity": {"value": "http://example.org/entity3"},
                        "nextValue": {"value": "NONE"}
                    }
                ]
            }
        }
        
        mock_sparql.query.return_value.convert.return_value = mock_results
        
        # Test first chain
        result = get_entity_position_in_sequence(
            "http://example.org/entity1", self.subject_uri, 
            self.predicate_uri, self.order_property
        )
        assert result == 1
        
        result = get_entity_position_in_sequence(
            "http://example.org/entity2", self.subject_uri, 
            self.predicate_uri, self.order_property
        )
        assert result == 2
        
        # Test single element chain
        result = get_entity_position_in_sequence(
            "http://example.org/entity3", self.subject_uri, 
            self.predicate_uri, self.order_property
        )
        assert result == 1

    @patch('heritrace.utils.shacl_utils.get_sparql')
    def test_with_sparql_query_empty_results(self, mock_get_sparql):
        """Test with SPARQL query returning empty results."""
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        # Mock empty query results
        mock_results = {
            "results": {
                "bindings": []
            }
        }
        
        mock_sparql.query.return_value.convert.return_value = mock_results
        
        result = get_entity_position_in_sequence(
            self.entity_uri, self.subject_uri, 
            self.predicate_uri, self.order_property
        )
        assert result is None

    def test_with_snapshot_simple_chain(self):
        """Test with RDFLib Graph snapshot for a simple chain."""
        # Create test graph
        snapshot = Graph()
        
        # Add ordered entities to the subject
        snapshot.add((URIRef(self.subject_uri), URIRef(self.predicate_uri), URIRef("http://example.org/entity1")))
        snapshot.add((URIRef(self.subject_uri), URIRef(self.predicate_uri), URIRef("http://example.org/entity2")))
        snapshot.add((URIRef(self.subject_uri), URIRef(self.predicate_uri), URIRef("http://example.org/entity3")))
        
        # Add ordering relationships
        snapshot.add((URIRef("http://example.org/entity1"), URIRef(self.order_property), URIRef("http://example.org/entity2")))
        snapshot.add((URIRef("http://example.org/entity2"), URIRef(self.order_property), URIRef("http://example.org/entity3")))
        # entity3 has no next (end of chain)
        
        # Test each position
        result = get_entity_position_in_sequence(
            "http://example.org/entity1", self.subject_uri, 
            self.predicate_uri, self.order_property, snapshot
        )
        assert result == 1
        
        result = get_entity_position_in_sequence(
            "http://example.org/entity2", self.subject_uri, 
            self.predicate_uri, self.order_property, snapshot
        )
        assert result == 2
        
        result = get_entity_position_in_sequence(
            "http://example.org/entity3", self.subject_uri, 
            self.predicate_uri, self.order_property, snapshot
        )
        assert result == 3

    def test_with_snapshot_multiple_chains(self):
        """Test with RDFLib Graph snapshot for multiple chains."""
        snapshot = Graph()
        
        # Add entities from two different chains
        # Chain 1: chapter1 -> chapter2
        snapshot.add((URIRef(self.subject_uri), URIRef(self.predicate_uri), URIRef("http://example.org/chapter1")))
        snapshot.add((URIRef(self.subject_uri), URIRef(self.predicate_uri), URIRef("http://example.org/chapter2")))
        snapshot.add((URIRef("http://example.org/chapter1"), URIRef(self.order_property), URIRef("http://example.org/chapter2")))
        
        # Chain 2: appendixA (single element)
        snapshot.add((URIRef(self.subject_uri), URIRef(self.predicate_uri), URIRef("http://example.org/appendixA")))
        
        # Test first chain
        result = get_entity_position_in_sequence(
            "http://example.org/chapter1", self.subject_uri, 
            self.predicate_uri, self.order_property, snapshot
        )
        assert result == 1
        
        result = get_entity_position_in_sequence(
            "http://example.org/chapter2", self.subject_uri, 
            self.predicate_uri, self.order_property, snapshot
        )
        assert result == 2
        
        # Test single element chain
        result = get_entity_position_in_sequence(
            "http://example.org/appendixA", self.subject_uri, 
            self.predicate_uri, self.order_property, snapshot
        )
        assert result == 1

    @patch('heritrace.utils.shacl_utils.get_sparql')
    def test_with_snapshot_empty_graph(self, mock_get_sparql):
        """Test with empty RDFLib Graph snapshot."""
        # Since an empty Graph is falsy, it will go through the SPARQL path
        # We need to mock get_sparql for this test
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        mock_results = {
            "results": {
                "bindings": []
            }
        }
        mock_sparql.query.return_value.convert.return_value = mock_results
        
        snapshot = Graph()
        
        result = get_entity_position_in_sequence(
            self.entity_uri, self.subject_uri, 
            self.predicate_uri, self.order_property, snapshot
        )
        assert result is None

    def test_with_empty_snapshot_proper_check(self):
        """Test with empty snapshot using proper None check instead of truthiness."""
        # This test demonstrates the current behavior - empty graphs are falsy
        # If the function used 'if snapshot is not None:' instead of 'if snapshot:'
        # this would work differently
        snapshot = Graph()
        
        # Since empty Graph is falsy, it goes through SPARQL path which fails in tests
        # This is a design consideration for the actual function
        with patch('heritrace.utils.shacl_utils.get_sparql') as mock_get_sparql:
            mock_sparql = MagicMock()
            mock_get_sparql.return_value = mock_sparql
            mock_sparql.query.return_value.convert.return_value = {"results": {"bindings": []}}
            
            result = get_entity_position_in_sequence(
                self.entity_uri, self.subject_uri, 
                self.predicate_uri, self.order_property, snapshot
            )
            assert result is None

    def test_with_snapshot_entity_not_found(self):
        """Test with snapshot where entity is not found."""
        snapshot = Graph()
        
        # Add some other entities but not the one we're looking for
        snapshot.add((URIRef(self.subject_uri), URIRef(self.predicate_uri), URIRef("http://example.org/other1")))
        snapshot.add((URIRef(self.subject_uri), URIRef(self.predicate_uri), URIRef("http://example.org/other2")))
        snapshot.add((URIRef("http://example.org/other1"), URIRef(self.order_property), URIRef("http://example.org/other2")))
        
        result = get_entity_position_in_sequence(
            self.entity_uri, self.subject_uri, 
            self.predicate_uri, self.order_property, snapshot
        )
        assert result is None

    @patch('heritrace.utils.shacl_utils.get_sparql')
    def test_sparql_query_construction(self, mock_get_sparql):
        """Test that the SPARQL query is constructed correctly."""
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        mock_results = {
            "results": {
                "bindings": []
            }
        }
        mock_sparql.query.return_value.convert.return_value = mock_results
        
        get_entity_position_in_sequence(
            self.entity_uri, self.subject_uri, 
            self.predicate_uri, self.order_property
        )
        
        # Verify SPARQL query was called
        mock_sparql.setQuery.assert_called_once()
        mock_sparql.setReturnFormat.assert_called_once()
        mock_sparql.query.assert_called_once()
        
        # Check the query contains the expected URIs
        query_call = mock_sparql.setQuery.call_args[0][0]
        assert self.subject_uri in query_call
        assert self.predicate_uri in query_call
        assert self.order_property in query_call
        assert "COALESCE(?next, \"NONE\")" in query_call

    def test_with_snapshot_complex_ordering(self):
        """Test with complex ordering scenario using realistic cultural heritage data."""
        snapshot = Graph()
        
        book_uri = "http://heritrace.org/book/1"
        has_part = "http://purl.org/vocab/frbr/core#part"
        next_part = "http://heritrace.org/vocabulary/nextPart"
        
        # Create a book with chapters and sections
        # Chapter 1 -> Chapter 2 -> Chapter 3
        chapter1 = "http://heritrace.org/chapter/1"
        chapter2 = "http://heritrace.org/chapter/2" 
        chapter3 = "http://heritrace.org/chapter/3"
        
        snapshot.add((URIRef(book_uri), URIRef(has_part), URIRef(chapter1)))
        snapshot.add((URIRef(book_uri), URIRef(has_part), URIRef(chapter2)))
        snapshot.add((URIRef(book_uri), URIRef(has_part), URIRef(chapter3)))
        
        snapshot.add((URIRef(chapter1), URIRef(next_part), URIRef(chapter2)))
        snapshot.add((URIRef(chapter2), URIRef(next_part), URIRef(chapter3)))
        
        # Test the ordering
        assert get_entity_position_in_sequence(chapter1, book_uri, has_part, next_part, snapshot) == 1
        assert get_entity_position_in_sequence(chapter2, book_uri, has_part, next_part, snapshot) == 2
        assert get_entity_position_in_sequence(chapter3, book_uri, has_part, next_part, snapshot) == 3
        
        # Test non-existent chapter
        chapter4 = "http://heritrace.org/chapter/4"
        assert get_entity_position_in_sequence(chapter4, book_uri, has_part, next_part, snapshot) is None

    @patch('heritrace.utils.shacl_utils.get_sparql')
    def test_malformed_sparql_results(self, mock_get_sparql):
        """Test handling of malformed SPARQL results."""
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        # Mock malformed results (missing expected structure)
        mock_results = {
            "results": {
                # Missing bindings key
            }
        }
        
        mock_sparql.query.return_value.convert.return_value = mock_results
        
        result = get_entity_position_in_sequence(
            self.entity_uri, self.subject_uri, 
            self.predicate_uri, self.order_property
        )
        assert result is None

    def test_with_snapshot_circular_reference(self):
        """Test with snapshot containing circular references."""
        snapshot = Graph()
        
        # Create circular reference: entity1 -> entity2 -> entity1
        snapshot.add((URIRef(self.subject_uri), URIRef(self.predicate_uri), URIRef("http://example.org/entity1")))
        snapshot.add((URIRef(self.subject_uri), URIRef(self.predicate_uri), URIRef("http://example.org/entity2")))
        snapshot.add((URIRef("http://example.org/entity1"), URIRef(self.order_property), URIRef("http://example.org/entity2")))
        snapshot.add((URIRef("http://example.org/entity2"), URIRef(self.order_property), URIRef("http://example.org/entity1")))
        
        # Should return None due to circular reference (no valid starting point)
        result = get_entity_position_in_sequence(
            "http://example.org/entity1", self.subject_uri, 
            self.predicate_uri, self.order_property, snapshot
        )
        assert result is None
