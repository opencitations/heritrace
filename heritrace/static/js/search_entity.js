// Cache object to store search results keyed by the complete search parameters
const searchCache = {};

// Function to generate a cache key from search parameters
function generateCacheKey(term, entityType, predicate) {
    return `${term}|${entityType || ''}|${predicate || ''}`;
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

// Function to execute the SPARQL search
function searchEntities(term, entityType = null, predicate = null, callback) {
    const input = $('.newEntityPropertyContainer input:focus');
    const contextData = input.length ? collectContextData(input) : {};

    // Genera una chiave di cache che include il contesto
    const cacheKey = `${term}|${entityType || ''}|${predicate || ''}|${JSON.stringify(contextData)}`;
    
    if (searchCache[cacheKey]) {
        lastSearchResults = searchCache[cacheKey];
        callback(null, { results: { bindings: searchCache[cacheKey] } });
        return;
    }

    let sparqlQuery = `
        SELECT DISTINCT ?entity ?type WHERE {
    `;

    if (entityType) {
        sparqlQuery += `
            ?entity a <${entityType}> .
        `;
    }

    // Aggiunge le triple dal contesto come vincoli
    Object.entries(contextData).forEach(([predicateUri, values]) => {
        values.forEach((valueObj, index) => {
            const formattedValue = formatValueForSparql(valueObj);
            sparqlQuery += `
                ?entity <${predicateUri}> ${formattedValue} .
            `;
        });
    });

    // Aggiunge la condizione di ricerca sul termine
    if (predicate) {
        sparqlQuery += `
            ?entity <${predicate}> ?searchValue .
        `;
    } else {
        sparqlQuery += `
            ?entity ?searchPredicate ?searchValue .
        `;
    }
    
    sparqlQuery += `
        FILTER(REGEX(STR(?searchValue), "${term}", "i"))
        OPTIONAL { ?entity <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type }
    } 
    LIMIT 5
    `;
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
            searchCache[cacheKey] = response.results.bindings;
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
             style="z-index: 1; width: 100%;">
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
                   class="btn btn-outline-primary btn-sm" target="_blank">
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
function updateSearchResults(results, dropdown) {
    dropdown.empty();

    if (results.length) {
        // Get the object class to obtain the entity type
        const objectClass = findObjectClass(dropdown);

        results.forEach(entity => {
            // Fetch the human-readable version and store it
            $.ajax({
                url: '/human-readable-entity',
                method: 'POST',
                data: {
                    uri: entity.entity.value,
                    entity_class: objectClass
                },
                success: function(readableEntity) {
                    // Store the human-readable label
                    entity.humanReadableLabel = readableEntity;
                    dropdown.append(`
                        <button type="button" class="list-group-item list-group-item-action" data-entity-uri="${entity.entity.value}">
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
                    // In case of error, use the last part of the URI
                    const label = entity.entity.value.split('/').pop();

                    // Store the label
                    entity.humanReadableLabel = label;

                    dropdown.append(`
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
                }
            });
        });
    }

    // Add the "Create New" option only if it's an input field (not a display)
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

// Function to handle the selection of an entity
function handleEntitySelection(container, entity) {
    // Find the parent properties container
    const propertiesContainer = container.closest('.newEntityPropertiesContainer');

    // Store only the content that isn't the search results or spinner
    const originalContent = propertiesContainer.children()
        .not('.entity-search-results')
        .not('.search-spinner')
        .detach();
        
    // Save the original content in the container's data
    propertiesContainer.data('originalContent', originalContent);

    // Create the hidden input to store the selected entity's URI
    const hiddenInput = $('<input>')
        .attr('type', 'hidden')
        .val(entity.entity.value)
        .attr('data-entity-reference', 'true');

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
function enhanceInputWithSearch(input) {
    const container = input.closest('.newEntityPropertyContainer');

    if (!container.length) return;

    const objectClass = findObjectClass(container);

    if (!objectClass) return;

    // Prima rimuoviamo tutti gli handler esistenti
    input.off('input');

    // Determina il predicato corretto da usare
    let repeaterItem = container.closest('[data-repeater-item]');
    let predicateUri;
    
    if (repeaterItem.data('intermediate-relation')) {
        predicateUri = repeaterItem.data('connecting-property');
    } else {
        predicateUri = repeaterItem.data('predicate-uri');
    }

    // Add the search results dropdown and spinner
    const searchResults = createSearchDropdown();
    addLoadingSpinner(input);
    input.after(searchResults);
    
    // Handle input with debounce
    let searchTimeout;
    input.on('input', function() {
        const term = $(this).val().trim();
        const spinner = container.find('.search-spinner');
        
        clearTimeout(searchTimeout);
        searchResults.addClass('d-none').empty();
        spinner.addClass('d-none');
        
        // Remove the is-invalid class when the user starts typing
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

    // Handle clicks on the results
    searchResults.on('click', '.list-group-item:not(.create-new)', function() {
        const entityUri = $(this).data('entity-uri');
        const entity = lastSearchResults.find(e => e.entity.value === entityUri);
        handleEntitySelection(container, entity);
    });

    // Handle the click on "Create New"
    searchResults.on('click', '.create-new', function() {
        input.trigger('focus');
        searchResults.addClass('d-none');
    });
}

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

// Initialize existing fields
$(document).ready(function() {
    $('[data-repeater-item]:not(.repeater-template)').find('input:visible').each(function() {
        enhanceInputWithSearch($(this));
    });
});