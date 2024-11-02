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

    // Rimuovi la classe is-invalid quando inizia una nuova ricerca
    const input = $('.newEntityPropertiesContainer input:focus');
    if (input.length) {
        input.removeClass('is-invalid');
        input.siblings('.invalid-feedback').hide();
    }

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

// Funzione per aggiungere lo spinner al campo
function addLoadingSpinner(input) {
    const spinnerHtml = `
        <div class="position-absolute end-0 top-50 translate-middle-y pe-2 search-spinner d-none">
            <div class="spinner-border spinner-border-sm text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    input.parent().css('position', 'relative').append(spinnerHtml);
}

// Funzione per creare la visualizzazione di un'entità selezionata
function createEntityDisplay(entity, container, callback) {
    const objectClass = findObjectClass(container);
    
    // Prima creiamo un elemento temporaneo
    const display = $(`
        <div class="entity-reference-display d-flex justify-content-between align-items-center p-2 border rounded">
            <div>
                <span class="entity-label">...</span>
                <div class="text-muted small d-none">${entity.entity.value}</div>
            </div>
            <div class="d-flex gap-2">
                <button type="button" class="btn btn-outline-secondary btn-sm change-entity">
                    <i class="bi bi-pencil"></i>
                </button>
                <a href="/about/${encodeURIComponent(entity.entity.value)}" 
                   class="btn btn-outline-primary btn-sm"
target="_blank">                    <i class="bi bi-box-arrow-up-right"></i>
                </a>
            </div>
        </div>
    `);

    // Poi facciamo la chiamata per ottenere la versione human readable
    $.ajax({
        url: '/human-readable-entity',
        method: 'POST',
        data: {
            uri: entity.entity.value,
            entity_class: objectClass
        },
        success: function(readableEntity) {
            display.find('.entity-label').text(readableEntity);
            if (callback) callback(display);
        },
        error: function() {
            // Fallback alla label o all'URI in caso di errore
            const label = entity.label ? 
                entity.label.value : 
                entity.entity.value.split('/').pop();
            display.find('.entity-label').text(label);
            if (callback) callback(display);
        }
    });

    return display;
}

// Funzione per aggiornare i risultati della ricerca
function updateSearchResults(results, dropdown) {
    dropdown.empty();

    if (results.length) {
        // Prima ottieni l'oggetto della ricerca per ottenere il tipo di entità
        const objectClass = findObjectClass(dropdown);

        results.forEach(entity => {
            // Effettua una chiamata per ottenere la versione human readable dell'entità
            $.ajax({
                url: '/human-readable-entity',
                method: 'POST',
                data: {
                    uri: entity.entity.value,
                    entity_class: objectClass
                },
                success: function(readableEntity) {
                    dropdown.append(`
                        <button type="button" class="list-group-item list-group-item-action">
                            <div class="d-flex justify-content-between align-items-center">
                                <div class="overflow-hidden me-2">
                                    <div class="text-truncate">${readableEntity}</div>
                                </div>
                                <i class="bi bi-chevron-right flex-shrink-0"></i>
                            </div>
                        </button>
                    `);
                },
                error: function() {
                    // In caso di errore, usa la label se disponibile o l'ultima parte dell'URI
                    const label = entity.label ? 
                        entity.label.value : 
                        entity.entity.value.split('/').pop();
                        
                    dropdown.append(`
                        <button type="button" class="list-group-item list-group-item-action">
                            <div class="d-flex justify-content-between align-items-center">
                                <div class="overflow-hidden me-2">
                                    <div class="fw-bold text-truncate">${label}</div>
                                    <small class="text-muted text-truncate d-block">${entity.entity.value}</small>
                                </div>
                                <i class="bi bi-chevron-right flex-shrink-0"></i>
                            </div>
                        </button>
                    `);
                }
            });
        });
    }

    // Aggiungi l'opzione "Create New" solo se è un campo di input (non un display)
    if (dropdown.prev().is('input')) {
        dropdown.append(`
            <button type="button" class="list-group-item list-group-item-action create-new">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="text-truncate">${results.length ? 'Create new entity' : 'No results found. Create new entity?'}</div>
                    <i class="bi bi-plus-circle flex-shrink-0 ms-2"></i>
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
    
    createEntityDisplay(entity, container, function(display) {
        input.hide().after(hiddenInput).after(display);
    });
    
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
    
    // Aggiungi il dropdown dei risultati e lo spinner
    const searchResults = createSearchDropdown();
    addLoadingSpinner(input);
    input.after(searchResults);
    
    // Gestisci l'input con debounce
    let searchTimeout;
    input.on('input', function() {
        const term = $(this).val().trim();
        const spinner = container.find('.search-spinner');
        
        clearTimeout(searchTimeout);
        searchResults.addClass('d-none').empty();
        spinner.addClass('d-none');
        
        // Rimuovi la classe is-invalid quando l'utente inizia a digitare
        $(this).removeClass('is-invalid');
        $(this).siblings('.invalid-feedback').hide();
        
        if (term.length < 3) return;
        
        spinner.removeClass('d-none');
        searchTimeout = setTimeout(() => {
            searchEntities(term, objectClass, predicateUri, function(error, response) {
                spinner.addClass('d-none');
                
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
        const index = $(this).index() - 1; // Sottraiamo 1 per compensare il pulsante "Create new"
        handleEntitySelection(container, lastSearchResults[index]);
    });

    // Gestisci il click su "Create New"
    searchResults.on('click', '.create-new', function() {
        input.trigger('focus');
        searchResults.addClass('d-none');
    });

    // Chiudi i risultati quando si clicca fuori
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.newEntityPropertiesContainer').length) {
            searchResults.addClass('d-none');
            container.find('.search-spinner').addClass('d-none');
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