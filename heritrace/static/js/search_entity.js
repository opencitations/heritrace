let lastSearchResults = []; // Global variable to keep track of results

// Function to execute the SPARQL search
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

    // Remove the is-invalid class when a new search starts
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
        <div class="entity-reference-display d-flex justify-content-between align-items-center p-2 border rounded">
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
                    // In case of error, use the label or the last part of the URI
                    const label = entity.label ? 
                        entity.label.value : 
                        entity.entity.value.split('/').pop();

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

// Function to find the object-class in the closest repeater-list that has it
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

// Function to enhance existing input fields with search functionality
function enhanceInputWithSearch(input) {
    const container = input.closest('.newEntityPropertiesContainer');
    if (!container.length) return;

    const objectClass = findObjectClass(container);
    if (!objectClass) return;

    const predicateUri = container.closest('[data-repeater-item]').data('predicate-uri');
    
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

    // Close the results when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.newEntityPropertiesContainer').length) {
            searchResults.addClass('d-none');
            container.find('.search-spinner').addClass('d-none');
        }
    });
}

// Function to handle changing a selected entity
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

// Override the existing initializeNewItem function
const originalInitializeNewItem = window.initializeNewItem;
window.initializeNewItem = function($newItem, isInitialStructure) {
    originalInitializeNewItem($newItem, isInitialStructure);
    
    $newItem.find('input').each(function() {
        enhanceInputWithSearch($(this));
    });
};

// Initialize existing fields
$(document).ready(function() {
    $('[data-repeater-item]:not(.repeater-template)').find('input').each(function() {
        enhanceInputWithSearch($(this));
    });
});