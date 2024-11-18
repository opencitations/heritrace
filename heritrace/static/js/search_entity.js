// Cache object to store search results keyed by the complete search parameters
const searchCache = {
    results: {},    // Store results by cache key and offset
    offset: {},     // Store current offset for each search
    lastResults: {} // Store last results for entity selection
};

// Function to generate a cache key from search parameters
function generateCacheKey(term, entityType, predicate, contextData, depth, connectingPredicate) {
    return `${term}|${entityType || ''}|${predicate || ''}|${JSON.stringify(contextData)}|${depth}|${connectingPredicate || ''}`;
}

// Raccoglie tutte le coppie predicato-valore dal contesto corrente
function collectContextData(currentInput) {
    const contextData = {};
    const currentInputUri = currentInput.data('predicate-uri');

    // Trova il container più vicino che contiene tutti i campi correlati
    const container = currentInput.closest('.newEntityPropertiesContainer');
    
    // Raccoglie i valori da tutti gli input/select visibili nel container
    container.find('input:visible, select:visible, input[data-mandatory-value="true"], textarea:visible').each(function() {
        const input = $(this);
        const propertyUri = input.data('predicate-uri');

        // Salta l'input corrente e quelli senza predicato
        if (!propertyUri || propertyUri === currentInputUri || input.is(currentInput) || propertyUri == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type') {
            return;
        }
        
        const value = input.val() || input.data('value');
        if (value && value.trim() !== "") {

            const datatypes = input.data('datatypes')?.split(',') || [];

            if (!contextData[propertyUri]) {
                contextData[propertyUri] = [];
            }
            contextData[propertyUri].push({
                value: value,
                datatypes: datatypes
            });
        }
    });
    
    return contextData;
}

// Funzione helper per formattare il valore in base al suo tipo
function formatValueForSparql(valueObj) {
    const value = valueObj.value;
    
    // Se non ci sono datatype, è un URI
    if (!valueObj.datatypes?.length) {
        return `<${value}>`;
    }
    
    // Altrimenti è un letterale con datatype
    return `"${value}"^^<${valueObj.datatypes[0]}>`;
}

function generateSearchQuery(term, entityType, predicate, dataset_db_triplestore, dataset_db_text_index_enabled, depth, connectingPredicate, offset = 0) {
    let query;
    if (dataset_db_text_index_enabled && dataset_db_triplestore === 'virtuoso') {
        // Use Virtuoso text index
        query = `
            SELECT DISTINCT ?entity ?type ?scoreValue WHERE {
                ${depth > 1 ? `
                    ?entity a <${entityType}> .
                    ?entity <${connectingPredicate}> ?nestedEntity .
                    ?nestedEntity <${predicate}> ?text .
                ` : `
                    ?entity ?p ?text .
                    ${entityType ? `?entity a <${entityType}> .` : ''}
                    ${predicate ? `?entity <${predicate}> ?text .` : ''}
                `}
                ?text bif:contains "'${term}*'" OPTION (score ?scoreValue) .
                OPTIONAL { ?entity a ?type }
                FILTER(?scoreValue > 0.2)
            }
            ORDER BY DESC(?scoreValue) ASC(?entity)
            OFFSET ${offset}
            LIMIT 5
        `;
    } else {
        // Fallback to standard REGEX search
        query = `
            SELECT DISTINCT ?entity ?type WHERE {
                ${depth > 1 ? `
                    ?entity a <${entityType}> .
                    ?entity <${connectingPredicate}> ?nestedEntity .
                    ?nestedEntity <${predicate}> ?searchValue .
                ` : `
                    ${entityType ? `?entity a <${entityType}> .` : ''}
                    ${predicate ? 
                        `?entity <${predicate}> ?searchValue .` :
                        `?entity ?searchPredicate ?searchValue .`
                    }
                `}
                FILTER(REGEX(STR(?searchValue), "${term}", "i"))
                OPTIONAL { ?entity a ?type }
            } 
            ORDER BY ASC(?entity)
            OFFSET ${offset}
            LIMIT 5
        `;
    }
    return query;
}

// Function to find the parent object class based on the current depth
function findParentObjectClass(element) {
    let current = $(element);
    let depth = parseInt(current.data('depth')) || 0;
    let parentDepth = depth - 1;
    while (current.length) {
        const repeaterList = current.closest('[data-repeater-list]');
        if (!repeaterList.length) break;

        const objectClass = repeaterList.data('class');
        const currentDepth = parseInt(repeaterList.data('depth')) || 0;
        if (objectClass && objectClass != 'None' && currentDepth === parentDepth) {
            return objectClass;
        }

        current = repeaterList.parent();
    }
    return null;
}

function findConnectingPredicate(input) {
    const currentRepeaterItem = input.closest('[data-repeater-item]');
    if (currentRepeaterItem.length) {
        const parentRepeaterItem = currentRepeaterItem.parent().closest('[data-repeater-item]');
        if (parentRepeaterItem.length) {
            const connectingPredicate = parentRepeaterItem.data('predicate-uri');
            return connectingPredicate;
        }
    }
    return null;
}

// Function to execute the SPARQL search
function searchEntities(term, entityType = null, predicate = null, callback, offset = 0) {
    const input = $('.newEntityPropertyContainer input:focus');
    const contextData = input.length ? collectContextData(input) : {};
    const depth = parseInt(input.data('depth')) || 0;

    if (depth > 1) {
        const parentClass = findParentObjectClass(input);
        if (parentClass) {
            entityType = parentClass;
        }
    }

    let connectingPredicate = null;
    if (depth > 1) {
        connectingPredicate = findConnectingPredicate(input);
    }

    const cacheKey = generateCacheKey(term, entityType, predicate, contextData, depth, connectingPredicate);

    // Initialize cache structures if they don't exist
    if (!searchCache.results[cacheKey]) {
        searchCache.results[cacheKey] = {};
    }
    if (typeof searchCache.offset[cacheKey] === 'undefined') {
        searchCache.offset[cacheKey] = 0;
    }

    // Use provided offset or the cached one
    const currentOffset = offset || searchCache.offset[cacheKey];

    // If we have cached results for this offset, use them
    if (searchCache.results[cacheKey][currentOffset]) {
        searchCache.lastResults[cacheKey] = searchCache.results[cacheKey][currentOffset];
        callback(null, { results: { bindings: searchCache.results[cacheKey][currentOffset] } });
        return;
    }

    let sparqlQuery = generateSearchQuery(
        term, 
        entityType, 
        predicate, 
        window.dataset_db_triplestore, 
        window.dataset_db_text_index_enabled, 
        depth, 
        connectingPredicate,
        currentOffset
    );

    let contextConstraints = '';
    Object.entries(contextData).forEach(([predicateUri, values]) => {
        values.forEach(valueObj => {
            const formattedValue = formatValueForSparql(valueObj);
            if (depth > 1) {
                contextConstraints += `\n    ?nestedEntity <${predicateUri}> ${formattedValue} .`;
            } else {
                contextConstraints += `\n    ?entity <${predicateUri}> ${formattedValue} .`;
            }
        });
    });

    sparqlQuery = sparqlQuery.replace('WHERE {', `WHERE {${contextConstraints}`);

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
            // Cache the results for this offset
            searchCache.results[cacheKey][currentOffset] = response.results.bindings;
            // Concatenate new results with existing lastResults
            if (searchCache.lastResults[cacheKey]) {
                searchCache.lastResults[cacheKey] = searchCache.lastResults[cacheKey].concat(response.results.bindings);
            } else {
                searchCache.lastResults[cacheKey] = response.results.bindings;
            }
            callback(null, response);
        },
        error: function(error) {
            callback(error);
        }
    });
}

// Function to create the search results dropdown
function createSearchDropdown() {
    return $(`
        <div class="entity-search-results list-group position-absolute d-none" 
             style="z-index: 1000; width: 100%; max-height: 400px; overflow-y: auto;">
        </div>
    `);
}

// Function to add a loading spinner to the input field
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

// Function to create the display of a selected entity
function createEntityDisplay(entity, container, callback) {
    const objectClass = findObjectClass(container);

    // Create a temporary element
    const display = $(`
        <div class="entity-reference-display d-flex justify-content-between align-items-center border rounded w-75">
            <div>
                <span class="entity-label">...</span>
                <div class="text-muted small d-none">${entity.entity.value}</div>
            </div>
            <div class="d-flex gap-2">
                <button type="button" class="btn btn-outline-secondary btn-sm change-entity" title="Clear selection">
                    <i class="bi bi-x-lg"></i>
                </button>
                <a href="/about/${encodeURIComponent(entity.entity.value)}" 
                   class="btn btn-outline-primary btn-sm redirection-btn" target="_blank">
                    <i class="bi bi-box-arrow-up-right"></i>
                </a>
            </div>
        </div>
    `);

    // Use the stored human-readable label if available
    if (entity.humanReadableLabel) {
        display.find('.entity-label').text(entity.humanReadableLabel);
        if (callback) callback(display);
    } else {
        // Fetch the human-readable version if not already fetched
        $.ajax({
            url: '/human-readable-entity',
            method: 'POST',
            data: {
                uri: entity.entity.value,
                entity_class: objectClass
            },
            success: function(readableEntity) {
                display.find('.entity-label').text(readableEntity);
                // Store it for future use
                entity.humanReadableLabel = readableEntity;
                if (callback) callback(display);
            },
            error: function() {
                // Fallback to label or URI in case of error
                const label = entity.label ? 
                    entity.label.value : 
                    entity.entity.value.split('/').pop();
                display.find('.entity-label').text(label);
                if (callback) callback(display);
            }
        });
    }

    return display;
}

// Function to update the search results
// Function to update the search results
function updateSearchResults(results, dropdown, input, depth, isLoadMore = false) {
    // Se non è un "load more", svuota il dropdown e scrollalo in cima
    if (!isLoadMore) {
        dropdown.empty();
        dropdown.scrollTop(0);
    } else {
        // Se è un "load more", rimuovi il vecchio pulsante "Ask for more"
        dropdown.find('.load-more-results').remove();
    }

    // Aggiungi il pulsante "Create New" all'inizio se applicabile
    if (dropdown.prev().is('input') && !dropdown.find('.create-new').length) {
        const createNewBtn = $(`
            <button type="button" class="list-group-item list-group-item-action create-new sticky-top bg-light">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="text-truncate">${results.length ? 'Create new entity' : 'No results found. Create new entity?'}</div>
                    <i class="bi bi-plus-circle flex-shrink-0 ms-2"></i>
                </div>
            </button>
        `);
        dropdown.prepend(createNewBtn);
    }

    if (results.length) {
        let objectClass;
        if (depth > 1) {
            objectClass = findParentObjectClass(input);
        } else {
            objectClass = findObjectClass(input);
        }

        results.forEach(entity => {
            $.ajax({
                url: '/human-readable-entity',
                method: 'POST',
                data: {
                    uri: entity.entity.value,
                    entity_class: objectClass
                },
                success: function(readableEntity) {
                    entity.humanReadableLabel = readableEntity;

                    // Aggiungi la voce al dropdown
                    const resultItem = $(`
                        <button type="button" class="list-group-item list-group-item-action" data-entity-uri="${entity.entity.value}">
                            <div class="d-flex justify-content-between align-items-center">
                                <div class="overflow-hidden me-2">
                                    <div class="text-truncate">${readableEntity}</div>
                                </div>
                                <i class="bi bi-chevron-right flex-shrink-0"></i>
                            </div>
                        </button>
                    `);
                    // Memorizza l'entità direttamente sull'elemento della lista
                    resultItem.data('entity', entity);
                    // Aggiungi il risultato dopo il pulsante "Create New"
                    dropdown.find('.create-new').after(resultItem);

                    // Se è l'ultimo risultato e abbiamo caricato altri risultati,
                    // scorri fino al primo nuovo elemento
                    if (isLoadMore && entity === results[0]) {
                        const newItemPosition = dropdown.find('.list-group-item').length - results.length - 1;
                        const scrollTarget = dropdown.find('.list-group-item').eq(newItemPosition);
                        if (scrollTarget.length) {
                            scrollTarget[0].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        }
                    }
                },
                error: function() {
                    const label = entity.entity.value.split('/').pop();
                    entity.humanReadableLabel = label;

                    const resultItem = $(`
                        <button type="button" class="list-group-item list-group-item-action" data-entity-uri="${entity.entity.value}">
                            <div class="d-flex justify-content-between align-items-center">
                                <div class="overflow-hidden me-2">
                                    <div class="fw-bold text-truncate">${label}</div>
                                    <small class="text-muted text-truncate d-block">${entity.entity.value}</small>
                                </div>
                                <i class="bi bi-chevron-right flex-shrink-0"></i>
                            </div>
                        </button>
                    `);
                    resultItem.data('entity', entity);
                    // Aggiungi il risultato dopo il pulsante "Create New"
                    dropdown.find('.create-new').after(resultItem);
                }
            });
        });
    }

    // Aggiungi il pulsante "Ask for more" alla fine se ci sono più risultati
    if (results.length === 5) {
        const loadMoreBtn = $(`
            <button type="button" class="list-group-item list-group-item-action load-more-results sticky-bottom bg-light">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="text-truncate">Ask for more results</div>
                    <i class="bi bi-arrow-clockwise flex-shrink-0 ms-2"></i>
                </div>
            </button>
        `);
        dropdown.append(loadMoreBtn);
    }

    dropdown.removeClass('d-none');
}

const style = $(`
    <style>
        .entity-search-results {
            max-height: 400px;
            overflow-y: auto;
            overflow-x: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .entity-search-results .sticky-bottom {
            position: sticky;
            bottom: 0;
            z-index: 1;
            border-top: 1px solid rgba(0,0,0,0.125);
        }
        .entity-search-results::-webkit-scrollbar {
            width: 6px;
        }
        .entity-search-results::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        .entity-search-results::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 3px;
        }
        .entity-search-results::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
    </style>
`);

// Function to handle the selection of an entity
function handleEntitySelection(container, entity, depth) {
    let propertiesContainer = container.closest('.newEntityPropertiesContainer');
    if (depth > 1) {
        // Move up to the parent 'newEntityPropertiesContainer' at depth - 1
        for (let i = 1; i < depth; i++) {
            propertiesContainer = propertiesContainer.closest('[data-repeater-item]').parent().closest('.newEntityPropertiesContainer');
        }
    }
    // Store only the content that isn't the search results or spinner
    const originalContent = propertiesContainer.children()
        .not('.entity-search-results')
        .not('.search-spinner')
        .detach();

    // Save the original content in the container's data
    propertiesContainer.data('originalContent', originalContent);
    const objectClass = findObjectClass(container);
    propertiesContainer.attr('data-class', objectClass);
    // Create the hidden input to store the selected entity's URI
    const hiddenInput = $('<input>')
        .attr('type', 'hidden')
        .val(entity.entity.value)
        .attr('data-entity-reference', 'true')
        .attr('data-class', objectClass);

    // Create the display for the selected entity
    createEntityDisplay(entity, propertiesContainer, function(display) {
        // Clear any existing content first except search-related elements
        propertiesContainer.children()
            .not('.entity-search-results')
            .not('.search-spinner')
            .remove();

        // Append the hidden input and display to the container
        propertiesContainer.append(hiddenInput).append(display);
    });

    // Hide the search results dropdown and spinner
    propertiesContainer.find('.entity-search-results').addClass('d-none');
    propertiesContainer.find('.search-spinner').addClass('d-none');
}

// Function to find the object-class in the closest repeater-list that has it
function findObjectClass(element) {
    let current = $(element);
    while (current.length) {
        const repeaterList = current.closest('[data-repeater-list]');
        if (!repeaterList.length) break;
        
        const objectClass = repeaterList.data('class');

        if (objectClass && objectClass != 'None') {
            // Check if we're inside an intermediate relation
            const intermediateItem = current.closest('[data-intermediate-relation]');
            if (intermediateItem.length) {
                // Use the target class of the final entity instead of the intermediate one
                const innerRepeaterList = intermediateItem.find('.nested-form-container').first();
                if (innerRepeaterList.length && innerRepeaterList.data('class')) {
                    return innerRepeaterList.data('class');
                }
            }
            return objectClass;
        }
        
        current = repeaterList.parent();
    }
    return null;
}

// Function to enhance existing input fields with search functionality
// Function to enhance existing input fields with search functionality
function enhanceInputWithSearch(input) {
    const container = input.closest('.newEntityPropertyContainer');
    const depth = parseInt(input.data('depth')) || 0;
    if (!depth > 0) return;
    if (!container.length) return;

    const objectClass = findObjectClass(container);
    if (!objectClass) return;

    // Rimuoviamo gli handler esistenti
    input.off('input');

    // Determina il predicato corretto
    let repeaterItem = container.closest('[data-repeater-item]');
    let predicateUri;
    
    if (repeaterItem.data('intermediate-relation')) {
        predicateUri = repeaterItem.data('connecting-property');
    } else {
        predicateUri = repeaterItem.data('predicate-uri');
    }

    // Aggiungi dropdown e spinner
    const searchResults = createSearchDropdown();
    addLoadingSpinner(input);
    input.after(searchResults);
    
    // Handle input con debounce
    let searchTimeout;

    input.on('input', function() {
        const term = $(this).val().trim();
        const spinner = container.find('.search-spinner');
        
        clearTimeout(searchTimeout);
        searchResults.addClass('d-none').empty();
        spinner.addClass('d-none');
        
        $(this).removeClass('is-invalid');
        $(this).siblings('.invalid-feedback').hide();
        
        if (term.length < 4) return;
        
        spinner.removeClass('d-none');
        searchTimeout = setTimeout(() => {
            searchEntities(term, objectClass, predicateUri, function(error, response) {
                spinner.addClass('d-none');
                
                if (error) {
                    console.error('Search failed:', error);
                    return;
                }

                updateSearchResults(response.results.bindings, searchResults, input, depth);
            });
        }, 300);
    });

    // Gestisci i click sui risultati
    searchResults.on('click', '.create-new', function() {
        input.trigger('focus');
        searchResults.addClass('d-none');
    });
}

// Initialize existing fields
$(document).ready(function() {
    $('[data-repeater-item]:not(.repeater-template)').find('input:visible').each(function() {
        enhanceInputWithSearch($(this));
    });

    $('head').append(style);

    // Handle clicks outside of search results
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.newEntityPropertyContainer').length) {
            $('.entity-search-results').addClass('d-none');
            $('.search-spinner').addClass('d-none');
        }
    });

    // Function to handle changing a selected entity
    $(document).on('click', '.change-entity', function(e) {
        e.preventDefault();
        const propertiesContainer = $(this).closest('.newEntityPropertiesContainer');
        const display = $(this).closest('.entity-reference-display');
        const hiddenInput = propertiesContainer.find('input[data-entity-reference="true"]');

        // Remove the display and hidden input
        display.remove();
        hiddenInput.remove();

        // Restore the original content
        const originalContent = propertiesContainer.data('originalContent');
        if (originalContent) {
            propertiesContainer.append(originalContent);
            propertiesContainer.removeData('originalContent');
        }

        // Re-initialize any inputs with search functionality
        propertiesContainer.find('input').each(function() {
            enhanceInputWithSearch($(this));
        });
    });

    $(document).on('click', '.load-more-results', function(e) {
        e.preventDefault();
        const dropdown = $(this).closest('.entity-search-results');
        const input = dropdown.prev('input');
        const term = input.val().trim();
        const depth = parseInt(input.data('depth')) || 0;
        
        // Get the object class and predicate
        let objectClass = depth > 1 ? findParentObjectClass(input) : findObjectClass(input);
        let repeaterItem = input.closest('[data-repeater-item]');
        let predicateUri = repeaterItem.data('intermediate-relation') 
            ? repeaterItem.data('connecting-property') 
            : repeaterItem.data('predicate-uri');
    
        // Generate the cache key
        const contextData = input.length ? collectContextData(input) : {};
        const connectingPredicate = depth > 1 ? findConnectingPredicate(input) : null;
        const cacheKey = `${term}|${objectClass || ''}|${predicateUri || ''}|${JSON.stringify(contextData)}|${depth}|${connectingPredicate || ''}`;
    
        // Increment the offset for this search
        searchCache.offset[cacheKey] = (searchCache.offset[cacheKey] || 0) + 5;
    
        // Show spinner in the "Load More" button
        const originalButtonContent = $(this).html();
        $(this).html('<div class="d-flex align-items-center justify-content-center"><div class="spinner-border spinner-border-sm me-2" role="status"></div>Loading...</div>');
    
        // Execute the search with the new offset
        searchEntities(term, objectClass, predicateUri, function(error, response) {
            if (error) {
                console.error('Search failed:', error);
                return;
            }
    
            // Update results with the new data
            updateSearchResults(response.results.bindings, dropdown, input, depth, true);
        }, searchCache.offset[cacheKey]);
    });

    $(document).on('click', '.entity-search-results .list-group-item:not(.create-new, .load-more-results)', function() {
        const entity = $(this).data('entity');
        const input = $(this).closest('.entity-search-results').prev('input');
        const depth = parseInt(input.data('depth')) || 0;
    
        if (entity) {
            handleEntitySelection(input.closest('.newEntityPropertyContainer'), entity, depth);
        }
    });
});