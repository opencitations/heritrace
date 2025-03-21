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



function generateSearchQuery(term, entityType, predicate, dataset_db_triplestore, dataset_db_text_index_enabled, connectingPredicate, offset = 0, searchTarget = 'self') {
    let query;
    // Use Virtuoso text index only if ALL these conditions are true:
    // 1. Term length >= 4 (Virtuoso requirement), AND
    // 2. Text index is enabled, AND
    // 3. Triplestore is virtuoso, AND
    // 4. Term does not contain spaces
    if (term.length >= 4 && dataset_db_text_index_enabled && dataset_db_triplestore === 'virtuoso' && !term.includes(' ') && !term.includes('-')) {
        // Use Virtuoso text index
        query = `
            SELECT DISTINCT ?entity ?scoreValue WHERE {
                ${searchTarget === 'parent' ? `
                    ?entity a <${entityType}> .
                    ?entity <${connectingPredicate}> ?nestedEntity .
                    ?nestedEntity <${predicate}> ?text .
                ` : `
                    ?entity ?p ?text .
                    ${entityType ? `?entity a <${entityType}> .` : ''}
                    ${predicate ? `?entity <${predicate}> ?text .` : ''}
                `}
                ?text bif:contains "'${term}*'" OPTION (score ?scoreValue) .
                FILTER(?scoreValue > 0.2)
            }
            ORDER BY DESC(?scoreValue) ASC(?entity)
            OFFSET ${offset}
            LIMIT 5
        `;
    } else {
        // Use standard REGEX search in all other cases
        query = `
            SELECT DISTINCT ?entity WHERE {
                ${searchTarget === 'parent' ? `
                    # For parent search, we optimize the order of triple patterns:
                    # 1. First filter by the specific predicate and search value (most restrictive)
                    ?nestedEntity <${predicate}> ?searchValue .
                    FILTER(REGEX(STR(?searchValue), "${term}", "i"))
                    # 2. Then connect to the parent entity (medium restrictive)
                    ?entity <${connectingPredicate}> ?nestedEntity .
                    # 3. Finally, filter by entity type (least restrictive)
                    ?entity a <${entityType}> .
                ` : `
                    ${entityType ? `?entity a <${entityType}> .` : ''}
                    ${predicate ? 
                        `?entity <${predicate}> ?searchValue .` :
                        `?entity ?searchPredicate ?searchValue .`
                    }
                    FILTER(REGEX(STR(?searchValue), "${term}", "i"))
                `}
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
    const input = $('.newEntityPropertyContainer input:focus, .newEntityPropertyContainer textarea:focus');
    const contextData = input.length ? collectContextData(input) : {};
    const searchTarget = input.data('search-target') || 'self';
    const connectingPredicate = findConnectingPredicate(input);
    
    // Determine the correct entity type based on search target
    let searchEntityType = entityType;
    if (searchTarget === 'parent') {
        searchEntityType = findParentObjectClass(input);
    }

    const cacheKey = generateCacheKey(term, searchEntityType, predicate, contextData, searchTarget, connectingPredicate);

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
        searchEntityType, 
        predicate, 
        window.dataset_db_triplestore, 
        window.dataset_db_text_index_enabled, 
        connectingPredicate,
        currentOffset,
        searchTarget
    );

    let contextConstraints = '';
    Object.entries(contextData).forEach(([predicateUri, values]) => {
        values.forEach(valueObj => {
            const formattedValue = formatValueForSparql(valueObj);
            if (searchTarget === 'parent') {
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
                <a href="/about/${entity.entity.value}" 
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
            url: '/api/human-readable-entity',
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
function updateSearchResults(results, dropdown, input, isLoadMore = false) {
    // Se non è un "load more", svuota il dropdown e scrollalo in cima
    if (!isLoadMore) {
        dropdown.empty();
        dropdown.scrollTop(0);
    } else {
        // Se è un "load more", rimuovi il vecchio pulsante "Ask for more"
        dropdown.find('.load-more-results').remove();
    }

    // Aggiungi il pulsante "Create New" all'inizio se applicabile
    if (dropdown.prev().is('input, textarea') && !dropdown.find('.create-new').length) {
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
        // Determine object class based on search target instead of depth
        const searchTarget = input.data('search-target') || 'self';
        let objectClass;
        if (searchTarget === 'parent') {
            objectClass = findParentObjectClass(input);
        } else {
            objectClass = findObjectClass(input);
        }

        results.forEach(entity => {
            $.ajax({
                url: '/api/human-readable-entity',
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
function handleEntitySelection(container, entity) {
    const input = container.find('input, textarea').first();
    const searchTarget = input.data('search-target') || 'self';
    let propertiesContainer = container.closest('.newEntityPropertiesContainer');
    
    if (searchTarget === 'parent') {
        // Move up to the parent container
        propertiesContainer = propertiesContainer.closest('[data-repeater-item]').parent().closest('.newEntityPropertiesContainer');
    }
    
    // Store only the content that isn't the search results or spinner
    const originalContent = propertiesContainer.children()
        .not('.entity-search-results')
        .not('.search-spinner')
        .detach();

    // Store the original depth value before detaching content
    const originalDepth = input.data('depth');
    
    // Save the original content in the container's data
    propertiesContainer.data('originalContent', originalContent);
    const objectClass = findObjectClass(container);
    propertiesContainer.attr('data-class', objectClass);
    
    // Create the hidden input to store the selected entity's URI
    const hiddenInput = $('<input>')
        .attr('type', 'hidden')
        .val(entity.entity.value)
        .attr('data-entity-reference', 'true')
        .attr('data-class', objectClass)
        .attr('data-depth', originalDepth); // Preserve the original depth

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

// Helper function to handle common input setup and event handling
function setupInputSearchHandling(input, container, resultsContainer, isParentSearch = false) {
    // Add loading spinner
    addLoadingSpinner(input);
    input.after(resultsContainer);
    
    // Handle input with debounce
    let searchTimeout;
    
    input.on('input', function() {
        const term = $(this).val().trim();
        const spinner = container.find('.search-spinner');
        const minCharsForSearch = parseInt($(this).data('min-chars-for-search')) || 4;
        
        // Clear previous search state
        clearTimeout(searchTimeout);
        resultsContainer.addClass('d-none');
        if (!isParentSearch) resultsContainer.empty();
        spinner.addClass('d-none');
        
        // Clear validation state
        $(this).removeClass('is-invalid');
        $(this).siblings('.invalid-feedback').hide();
        
        // Only search if we have enough characters
        if (term.length < minCharsForSearch) return;
        
        // Show loading indicator
        spinner.removeClass('d-none');
        
        // Return the timeout handle for potential cancellation
        return searchTimeout;
    });
    
    return searchTimeout;
}

// Helper function to find the connecting predicate for parent search
function findParentConnectingPredicate(repeaterItem) {
    // Get the parent container of the current repeater-list
    const currentRepeaterList = repeaterItem.closest('[data-repeater-list]');
    const parentContainer = currentRepeaterList.parent().closest('[data-repeater-item]');
    
    if (parentContainer.length) {
        // Get the connecting predicate from the parent repeater-item
        return parentContainer.data('predicate-uri');
    }
    
    return null;
}

// Helper function to apply context constraints to a SPARQL query
function applyContextConstraints(sparqlQuery, contextData, insertPoint) {
    let contextConstraints = '';
    
    // Build context constraints string
    Object.entries(contextData).forEach(([predicateUri, values]) => {
        values.forEach(valueObj => {
            const formattedValue = formatValueForSparql(valueObj);
            contextConstraints += `\n    ?nestedEntity <${predicateUri}> ${formattedValue} .`;
        });
    });
    
    // Apply constraints if we have any
    if (contextConstraints && insertPoint) {
        return sparqlQuery.replace(insertPoint, insertPoint + contextConstraints);
    }
    
    return sparqlQuery;
}

// Function to enhance existing input fields with search functionality
function enhanceInputWithSearch(input) {
    const container = input.closest('.newEntityPropertyContainer');
    const depth = parseInt(input.data('depth')) || 0;
    if (!depth > 0) return;
    if (!container.length) return;

    const objectClass = findObjectClass(container);
    if (!objectClass) return;

    // Remove existing handlers
    input.off('input');

    // Determine the correct predicate
    let repeaterItem = container.closest('[data-repeater-item]');
    let predicateUri;
    
    if (repeaterItem.data('intermediate-relation')) {
        predicateUri = repeaterItem.data('connecting-property');
    } else {
        predicateUri = repeaterItem.data('predicate-uri');
    }
    
    // Check if this is the special case: depth 1 with search_target='parent'
    const searchTarget = input.data('search-target') || 'self';
    if (depth === 1 && searchTarget === 'parent') {
        // Use top-level search functionality
        const suggestionsContainer = createTopLevelSuggestionContainer();
        let searchTimeout = setupInputSearchHandling(input, container, suggestionsContainer, true);
        
        // Handle parent search specific logic
        input.on('input', function() {
            const term = $(this).val().trim();
            const minCharsForSearch = parseInt($(this).data('min-chars-for-search')) || 4;
            const spinner = container.find('.search-spinner');
            
            // Skip if not enough characters
            if (term.length < minCharsForSearch) return;
            
            searchTimeout = setTimeout(() => {
                // Get parent entity type - special handling for different pages
                let parentEntityType;
                
                // Check if we're in about.jinja (where entity_type is a global string variable)
                if (typeof entity_type !== 'undefined' && typeof entity_type === 'string') {
                    parentEntityType = entity_type;
                } 
                // Otherwise use the regular DOM traversal method
                else {
                    parentEntityType = findParentObjectClass(input);
                }
                
                // Get connecting predicate from parent
                const connectingPredicate = findParentConnectingPredicate(repeaterItem);
                
                // Get value predicate
                const nestedEntityValuePredicate = input.data('predicate-uri');
                
                // Generate query
                let sparqlQuery = generateSearchQuery(
                    term,
                    parentEntityType,
                    nestedEntityValuePredicate,
                    window.dataset_db_triplestore,
                    window.dataset_db_text_index_enabled,
                    connectingPredicate,
                    0,
                    'parent'
                );
                
                // Apply context constraints
                const contextData = collectContextData(input);
                const insertPoint = '?nestedEntity <' + nestedEntityValuePredicate + '> ?searchValue .';
                sparqlQuery = applyContextConstraints(sparqlQuery, contextData, insertPoint);
                
                // Execute query
                $.ajax({
                    url: '/dataset-endpoint',
                    method: 'POST',
                    data: { query: sparqlQuery },
                    headers: { 'Accept': 'application/sparql-results+json' },
                    success: function(response) {
                        spinner.addClass('d-none');
                        updateTopLevelSuggestions(response.results.bindings, suggestionsContainer, parentEntityType);
                    },
                    error: function(error) {
                        spinner.addClass('d-none');
                        console.error('Search failed:', error);
                    }
                });
            }, 300);
        });
        
        // Handle close button click
        suggestionsContainer.find('.btn-close').on('click', function() {
            suggestionsContainer.addClass('d-none');
        });
        
        return; // Exit early as we've set up top-level search
    }

    // Regular entity search for all other cases
    const searchResults = createSearchDropdown();
    let searchTimeout = setupInputSearchHandling(input, container, searchResults);

    input.on('input', function() {
        const term = $(this).val().trim();
        const minCharsForSearch = parseInt($(this).data('min-chars-for-search')) || 4;
        const spinner = container.find('.search-spinner');
        
        // Skip if not enough characters
        if (term.length < minCharsForSearch) return;
        
        searchTimeout = setTimeout(() => {
            searchEntities(term, objectClass, predicateUri, function(error, response) {
                spinner.addClass('d-none');
                
                if (error) {
                    console.error('Search failed:', error);
                    return;
                }

                updateSearchResults(response.results.bindings, searchResults, input, false);
            });
        }, 300);
    });

    // Handle clicks on results
    searchResults.on('click', '.create-new', function() {
        input.trigger('focus');
        searchResults.addClass('d-none');
    });
}

// Initialize existing fields
$(document).ready(function() {
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
        
        // Store the depth before removal to ensure it's preserved
        const originalDepth = hiddenInput.data('depth');

        // Remove the display and hidden input
        display.remove();
        hiddenInput.remove();

        // Restore the original content
        const originalContent = propertiesContainer.data('originalContent');
        if (originalContent) {
            propertiesContainer.append(originalContent);
            propertiesContainer.removeData('originalContent');
            
            // Ensure that all inputs have their depth attribute explicitly set if needed
            propertiesContainer.find('input, textarea').each(function() {
                const input = $(this);
                if (typeof input.data('depth') === 'undefined' && originalDepth !== undefined) {
                    input.attr('data-depth', originalDepth);
                }
                enhanceInputWithSearch(input);
            });
        } else {
            console.warn('Original content not found when changing entity');
        }
    });

    $(document).on('click', '.load-more-results', function(e) {
        e.preventDefault();
        const dropdown = $(this).closest('.entity-search-results');
        const input = dropdown.prev('input, textarea');
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
            updateSearchResults(response.results.bindings, dropdown, input, true);
        }, searchCache.offset[cacheKey]);
    });

    $(document).on('click', '.entity-search-results .list-group-item:not(.create-new, .load-more-results)', function() {
        const entity = $(this).data('entity');
        const input = $(this).closest('.entity-search-results').prev('input, textarea');
    
        if (entity) {
            handleEntitySelection(input.closest('.newEntityPropertyContainer'), entity);
        }
    });
});