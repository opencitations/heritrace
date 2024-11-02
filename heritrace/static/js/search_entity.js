let lastSearchResults = []; // Variabile globale per tenere traccia dei risultati

// Funzione per eseguire la ricerca SPARQL
function searchEntities(term, entityType = null, predicate = null, callback) {
    let sparqlQuery = `
        SELECT DISTINCT ?entity ?label ?type WHERE {
            ?entity ?p ?o .
            OPTIONAL { ?entity <http://www.w3.org/2000/01/rdf-schema#label> ?label }
            OPTIONAL { ?entity <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type }
            FILTER(
                REGEX(STR(?entity), "${term}", "i") ||
                REGEX(STR(?o), "${term}", "i") 
            )
    `;

    if (entityType) {
        sparqlQuery += `?entity a <${entityType}> .`;
    }
    
    if (predicate) {
        sparqlQuery += `VALUES ?p { <${predicate}> }`;
    }

    sparqlQuery += `} LIMIT 5`;

    $.ajax({
        url: '/dataset-endpoint',
        method: 'POST',
        data: { query: sparqlQuery },
        headers: { 'Accept': 'application/sparql-results+json' },
        success: function(response) {
            lastSearchResults = response.results.bindings;
            callback(null, response);
        },
        error: function(error) {
            callback(error);
        }
    });
}

// Funzione per creare il dropdown dei risultati
function createSearchDropdown() {
    return $(`
        <div class="entity-search-results list-group position-absolute d-none" 
             style="z-index: 1; width: 100%;">
        </div>
    `);
}

// Funzione per creare la visualizzazione di un'entità selezionata
function createEntityDisplay(entity) {
    const label = entity.label ? entity.label.value : entity.entity.value.split('/').pop();
    return $(`
        <div class="entity-reference-display d-flex justify-content-between align-items-center p-2 border rounded">
            <div>
                <strong>${label}</strong>
                <div class="text-muted small">${entity.entity.value}</div>
            </div>
            <div class="d-flex gap-2">
                <button type="button" class="btn btn-outline-secondary btn-sm change-entity">
                    <i class="bi bi-pencil"></i>
                </button>
                <a href="/about/${encodeURIComponent(entity.entity.value)}" 
                   class="btn btn-outline-primary btn-sm"
                   target="_blank">
                    <i class="bi bi-box-arrow-up-right"></i>
                </a>
            </div>
        </div>
    `);
}

// Funzione per aggiornare i risultati della ricerca
function updateSearchResults(results, dropdown) {
    dropdown.empty();

    if (results.length) {
        results.forEach(entity => {
            const label = entity.label ? 
                entity.label.value : 
                entity.entity.value.split('/').pop();
                
            dropdown.append(`
                <button type="button" class="list-group-item list-group-item-action">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <div class="fw-bold">${label}</div>
                            <small class="text-muted">${entity.entity.value}</small>
                        </div>
                        <i class="bi bi-chevron-right"></i>
                    </div>
                </button>
            `);
        });
    }

    // Aggiungi l'opzione "Create New" solo se è un campo di input (non un display)
    if (dropdown.prev().is('input')) {
        dropdown.append(`
            <button type="button" class="list-group-item list-group-item-action create-new">
                <div class="d-flex justify-content-between align-items-center">
                    <div>${results.length ? 'Create new entity' : 'No results found. Create new entity?'}</div>
                    <i class="bi bi-plus-circle"></i>
                </div>
            </button>
        `);
    }

    dropdown.removeClass('d-none');
}

// Funzione per gestire la selezione di un'entità
function handleEntitySelection(container, entity) {
    const input = container.find('input');
    const hiddenInput = $('<input>')
        .attr('type', 'hidden')
        .val(entity.entity.value)
        .attr('data-entity-reference', 'true');
    
    const display = createEntityDisplay(entity);
    
    input.hide().after(hiddenInput).after(display);
    container.find('.entity-search-results').addClass('d-none');
}

// Funzione per trovare l'object-class nel repeater-list più vicino che ce l'ha
function findObjectClass(element) {
    let current = $(element);
    while (current.length) {
        const repeaterList = current.closest('[data-repeater-list]');
        if (!repeaterList.length) break;
        
        const objectClass = repeaterList.data('object-class');
        if (objectClass && objectClass != 'None') return objectClass;
        
        current = repeaterList.parent();
    }
    return null;
}

// Funzione per migliorare i campi input esistenti con la funzionalità di ricerca
function enhanceInputWithSearch(input) {
    const container = input.closest('.newEntityPropertiesContainer');
    if (!container.length) return;

    const objectClass = findObjectClass(container);
    if (!objectClass) return;

    const predicateUri = container.closest('[data-repeater-item]').data('predicate-uri');

    // Aggiungi il dropdown dei risultati
    const searchResults = createSearchDropdown();
    input.after(searchResults);
    
    // Gestisci l'input con debounce
    let searchTimeout;
    input.on('input', function() {
        const term = $(this).val().trim();
        
        clearTimeout(searchTimeout);
        searchResults.addClass('d-none').empty();
        
        if (term.length < 3) return;
        
        searchTimeout = setTimeout(() => {
            searchEntities(term, objectClass, predicateUri, function(error, response) {
                if (error) {
                    console.error('Search failed:', error);
                    return;
                }
                
                updateSearchResults(response.results.bindings, searchResults);
            });
        }, 300);
    });

    // Gestisci i click sui risultati
    searchResults.on('click', '.list-group-item:not(.create-new)', function() {
        const index = $(this).index();
        handleEntitySelection(container, lastSearchResults[index]);
    });

    // Chiudi i risultati quando si clicca fuori
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.newEntityPropertiesContainer').length) {
            searchResults.addClass('d-none');
        }
    });
}

// Funzione per gestire il cambio di un'entità selezionata
$(document).on('click', '.change-entity', function(e) {
    e.preventDefault();
    const container = $(this).closest('.newEntityPropertiesContainer');
    const display = $(this).closest('.entity-reference-display');
    const hiddenInput = container.find('input[data-entity-reference="true"]');
    const originalInput = container.find('input').first();
    
    display.remove();
    hiddenInput.remove();
    originalInput.show().val('').focus();
});

// Override della funzione initializeNewItem esistente
const originalInitializeNewItem = window.initializeNewItem;
window.initializeNewItem = function($newItem, isInitialStructure) {
    originalInitializeNewItem($newItem, isInitialStructure);
    
    $newItem.find('input').each(function() {
        enhanceInputWithSearch($(this));
    });
};

// Inizializzazione dei campi esistenti
$(document).ready(function() {
    $('[data-repeater-item]:not(.repeater-template)').find('input').each(function() {
        enhanceInputWithSearch($(this));
    });
});