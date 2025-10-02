// Store initial copies of repeater items
var initialCopies = {};

var pendingChanges = [];

var tempIdCounter = 0;


function generateUniqueId(prefix) {
    return prefix + '_' + Math.random().toString(36).substr(2, 9);
}

// Helper functions for collectFormData
function createIntermediateEntity(intermediateClass, intermediateShape, targetEntityType = null, targetShape = null) {
    let entity = {
        "entity_type": intermediateClass,
        "entity_shape": intermediateShape,
        "properties": {}
    };
    
    if (targetEntityType) {
        entity.targetEntityType = targetEntityType;
    }
    if (targetShape) {
        entity.targetShape = targetShape;
    }
    
    return entity;
}

function handleNestedProperties(container, objectClass, shape, shacl, depth) {
    let nestedProperties = {};
    collectFormData(container, nestedProperties, shacl, depth);
    
    if (Object.keys(nestedProperties).length > 0) {
        let nestedEntity = {
            "entity_type": objectClass,
            "entity_shape": shape,
            "properties": nestedProperties
        };
        
        return nestedEntity;
    }
    
    return null;
}

function enrichEntityWithMetadata(entity, additionalProperties, orderedBy, tempId) {
    if (additionalProperties) {
        Object.assign(entity.properties, additionalProperties);
    }

    if (orderedBy) {
        entity['orderedBy'] = orderedBy;
    }

    if (tempId) {
        entity['tempId'] = tempId;
    }
    
    return entity;
}

function ensurePropertyArray(data, propertyUri) {
    if (!data[propertyUri]) {
        data[propertyUri] = [];
    }
    return data[propertyUri];
}

function updateButtons(list, recursive = true) {
    const maxItems = parseInt(list.data('max-items')) || Infinity;
    const minItems = parseInt(list.data('min-items')) || 0;
    const items = list.children('[data-repeater-item]').not('.repeater-template');
    const addButton = list.children('[data-repeater-create]');

    // Gestione del pulsante di aggiunta
    if (items.length >= maxItems) {
        addButton.hide();
    } else {
        addButton.show();
    }

    // Gestione dei pulsanti di cancellazione
    items.each(function(index) {
        const deleteBtn = $(this).find('> .repeater-delete-btn');
        if (index < minItems) {
            deleteBtn.hide();
        } else {
            deleteBtn.show();
        }
    });

    // Gestione speciale per elementi opzionali singoli (max=1, min=0)
    if (maxItems === 1 && minItems === 0) {
        if (items.length === 0) {
            addButton.show();
        } else {
            addButton.hide();
            items.find('> .repeater-delete-btn').show();
        }
    }

    // Gestione ricorsiva per elementi annidati
    if (recursive) {
        items.each(function() {
            $(this).find('[data-repeater-list]').each(function() {
                updateButtons($(this), false);
            });
        });
    }
}

// Funzione per aggiornare la numerazione degli elementi ordinabili
function updateOrderedElementsNumbering() {
    $('[data-ordered-by]').each(function() {
        var labelGroups = {};

        // Raggruppa gli elementi per etichetta originale
        $(this).find('[data-repeater-item]').not('.repeater-template').each(function() {
            var label = $(this).find('.form-label').first();
            var originalText = label.data('original-text');
            if (!labelGroups[originalText]) {
                labelGroups[originalText] = [];
            }
            labelGroups[originalText].push(label);
        });

        // Aggiorna la numerazione per ogni gruppo
        Object.keys(labelGroups).forEach(function(originalText) {
            labelGroups[originalText].forEach(function(label, index) {
                label.text(originalText + ' ' + (index + 1));
            });
        });
    });
}

function initializeMandatoryElements(container) {
    // Batch enable all inputs first
    container.find(':input').prop('disabled', false);

    // Collect all operations to batch them
    var operationsQueue = [];
    
    container.find('[data-repeater-list]').each(function() {
        var list = $(this);
        var minItems = parseInt(list.data('min-items') || 0);
        var currentItems = list.children('[data-repeater-item]').not('.repeater-template').length;
        
        if (minItems > 0 && currentItems === 0) {
            var addButton = list.find('[data-repeater-create] .initial-structure-add');
            if (addButton.length) {
                operationsQueue.push({
                    button: addButton,
                    count: minItems
                });
            }
        }
    });

    // Process operations asynchronously to prevent UI blocking
    if (operationsQueue.length > 0) {
        processOperationsAsync(operationsQueue);
    }
}

function processOperationsAsync(operationsQueue) {
    if (operationsQueue.length === 0) return;
    
    var currentOperation = operationsQueue.shift();
    var button = currentOperation.button;
    var count = currentOperation.count;
    
    // Process clicks in smaller batches with timeouts
    var batchSize = Math.min(count, 3); // Process max 3 at a time
    var processed = 0;
    
    function processBatch() {
        for (var i = 0; i < batchSize && processed < count; i++) {
            button.click();
            processed++;
        }
        
        if (processed < count) {
            // Use setTimeout to yield control back to the browser
            setTimeout(processBatch, 10);
        } else {
            // Move to next operation
            setTimeout(function() {
                processOperationsAsync(operationsQueue);
            }, 10);
        }
    }
    
    processBatch();
}

async function initializeForm() {
    let selectedUri;
    let selectedShape;

    if ($('#entity_type').length) {
        const selectedOption = $('#entity_type option:selected');

        // Se l'opzione selezionata è quella predefinita (disabled) o non è selezionata alcuna opzione
        if (selectedOption.is(':disabled') || !selectedOption.val()) {
            // Seleziona automaticamente la prima opzione disponibile (non disabled)
            const firstAvailableOption = $('#entity_type option:not(:disabled):first');
            if (firstAvailableOption.length && firstAvailableOption.val()) {
                selectedUri = firstAvailableOption.val();
                selectedShape = firstAvailableOption.data('shape');
                $('#entity_type').val(selectedUri); // Imposta la selezione nel dropdown
            } else {
                // Nessuna opzione disponibile
                $('#dynamic-form-container .property-group').remove();
                $('#form-loading').hide();
                $('#form-error').hide();
                return;
            }
        } else {
            // Ottieni i valori dall'opzione già selezionata
            selectedUri = selectedOption.val();
            selectedShape = selectedOption.data('shape');
        }
    } else if (typeof entity_type !== 'undefined' && entity_type) {
        // In about.jinja, use the entity_type variable
        selectedUri = entity_type;
        selectedShape = typeof entity_shape !== 'undefined' ? entity_shape : '';
    }

    if (selectedUri) {
        await loadFormFieldsAsync(selectedUri, selectedShape);
    } else {
        // Clear form if no entity type selected
        $('#dynamic-form-container .property-group').remove();
        $('#form-loading').hide();
        $('#form-error').hide();
    }
}

async function loadFormFieldsAsync(entityClass, entityShape) {
    // Show loading indicator and hide previous content
    $('#form-loading').show();
    $('#form-error').hide();
    // Remove all existing content, not just .property-group
    $('#dynamic-form-container').children().not('#form-loading, #form-error').remove();

    try {
        // Step 1: Load form fields data from API
        const params = new URLSearchParams({
            entity_class: entityClass,
            entity_shape: entityShape
        });

        const formFieldsResponse = await fetch(
            `/api/form-fields?${params.toString()}`,
            {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }
        );

        if (!formFieldsResponse.ok) {
            throw new Error(`HTTP ${formFieldsResponse.status}: ${formFieldsResponse.statusText}`);
        }

        const formFieldsData = await formFieldsResponse.json();

        if (formFieldsData.status !== 'success') {
            throw new Error(formFieldsData.message || 'Failed to load form fields');
        }

        // Step 2: Render form fields as HTML
        const renderResponse = await fetch('/api/render-form-fields', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                entity_key: formFieldsData.entity_key
            })
        });

        if (!renderResponse.ok) {
            throw new Error(`HTML rendering failed: ${renderResponse.status} ${renderResponse.statusText}`);
        }

        const html = await renderResponse.text();

        // Step 3: Insert HTML into the page
        $('#dynamic-form-container').append(html);

        // Step 4: Initialize the form elements
        const $formContainer = $('#dynamic-form-container .property-group').last();

        if ($formContainer.length > 0) {
            // Show the form container
            $formContainer.show();

            // Initialize mandatory elements
            initializeMandatoryElements($formContainer);

            // Initialize tooltips
            $formContainer.find('[data-bs-toggle="tooltip"]').tooltip();

            // Initialize repeater functionality
            initializeRepeaters($formContainer);
        }

    } catch (error) {
        console.error('Error loading form fields:', error);
        showFormError(error.message);
    } finally {
        $('#form-loading').hide();
    }
}

function showFormError(message) {
    $('#form-error-message').text(message);
    $('#form-error').show();
}

function initializeRepeaters($container) {
    // Initialize repeaters for the new container
    $container.find('[data-repeater-list]').each(function() {
        var list = $(this);
        var firstItem = list.find('[data-repeater-item]').first();

        if (firstItem.length > 0) {
            var templateKey = list.data('repeater-list');

            // Only clone if we don't already have a template for this key
            if (!initialCopies[templateKey]) {
                initialCopies[templateKey] = firstItem.clone(true, true);
            }

            // Initialize Sortable for ordered lists
            if (list.data('ordered-by')) {
                updateSortable(list);
            }

            updateButtons(list);
        }
    });

    updateOrderedElementsNumbering();
}

function storePendingChange(action, subject, predicate, object, newObject = null, shape = null, entity_type = null, entity_shape = null, isVirtual = false) {
    // For 'update' actions, check if there's already a pending change for the same subject/predicate/object/shape
    if (action === 'update') {
        let existingChangeIndex = pendingChanges.findIndex(change =>
            change.action === 'update' &&
            change.subject === subject &&
            change.predicate === predicate &&
            change.object === object &&
            change.shape === shape
        );

        if (existingChangeIndex !== -1) {
            // Update the existing change with the new value
            pendingChanges[existingChangeIndex].newObject = newObject;
            return;
        }
    }

    // If no existing change found, add a new one
    const change = {
        action: action,
        subject: subject,
        predicate: predicate,
        object: object,
        newObject: newObject,
        shape: shape,
        entity_type: entity_type,
        entity_shape: entity_shape
    };

    if (isVirtual) {
        change.is_virtual = true;
    }

    pendingChanges.push(change);
}

// Funzione per inizializzare Sortable su un elemento
function initSortable(element) {
    new Sortable(element, {
        handle: '.drag-handle',
        animation: 150,
        draggable: '.draggable',
        filter: '.non-sortable', // Esclude elementi con questa classe
        onMove: function(evt) {
            return !evt.related.classList.contains('non-sortable');
        },
        onEnd: function(evt) {
            let new_order = [];
            let predicate = null;
            let orderedBy = null;
            let shape = null;
            
            // Get the shape from the first item to determine which shape group this is
            let firstItem = $(evt.from).find('.property-value').first();
            if (firstItem.length > 0) {
                predicate = firstItem.data('property-id');
                orderedBy = firstItem.data('ordered_by');
                shape = firstItem.data('shape') || '';
            }
            
            // Only collect items with the same shape
            $(evt.from).find('.property-value').each(function() {
                const itemShape = $(this).data('shape') || '';
                if (itemShape === shape) {
                    const objectId = $(this).data('old-object-id');
                    const tempId = $(this).data('temp-id');
                    if (objectId) {
                        new_order.push(objectId);
                    } else if (tempId) {
                        new_order.push(tempId);
                    }
                }
            });
            updateOrderedElementsNumbering();

            if (typeof subject === 'undefined' || subject === 'null' || subject === null) {
                return;
            }

            // Cerca un'azione di ordinamento esistente per questo predicato e shape
            let existingOrderIndex = pendingChanges.findIndex(change => 
                change.action === 'order' && 
                change.predicate === predicate &&
                change.shape === shape
            );

            if (existingOrderIndex !== -1) {
                // Aggiorna l'ordine esistente
                pendingChanges[existingOrderIndex].object = new_order;
            } else {
                // Aggiungi una nuova azione di ordinamento
                const currentEntityType = typeof entity_type !== 'undefined' ? entity_type : null;
                storePendingChange('order', subject, predicate, new_order, orderedBy, shape, currentEntityType);
            }
        }
    });
}

// Funzione per aggiornare la struttura Sortable dopo l'aggiunta di nuovi elementi
function updateSortable(list) {
    // Rimuovi la classe 'non-sortable' da tutti gli elementi
    list.find('[data-repeater-item]').removeClass('non-sortable');
    
    // Aggiungi la classe 'non-sortable' all'ultimo elemento (il pulsante "Add another...")
    list.children().last().addClass('non-sortable');
    
    // Reinizializza Sortable
    initSortable(list[0]);
}

function setRequiredForVisibleFields(item, isInitialStructure = false) {
    item.find('input, select, textarea').each(function() {
        var elem = $(this);
        var isVisible = elem.is(':visible');

        if (isVisible) {
            var parentRepeaterList = elem.closest('[data-repeater-list]');
            var isRequired = parentRepeaterList.length > 0 && 
                            (isInitialStructure || parseInt(parentRepeaterList.data('min-items') || 0) > 0);
            elem.prop('required', isVisible && isRequired);    
        }
    });
}

function showAppropriateDateInput(selector) {
    const dateInputGroup = selector.closest('.input-group');
    const selectedDateType = selector.val();

    // Hide all date input containers
    dateInputGroup.find('.date-input-container').addClass('d-none')
    dateInputGroup.find('.date-input').attr('disabled', true);

    // Show the selected date input container
    const inputToShow = dateInputGroup.find(`.date-input-container input[data-date-type="${selectedDateType}"]`).closest('.date-input-container');
    inputToShow.removeClass('d-none');
    inputToShow.find('.date-input').attr('disabled', false);
}

function initializeNewItem($newItem, isInitialStructure = false) {
    $newItem.addClass('added-in-edit-mode');

    if ($newItem.hasClass('draggable')) {
        $newItem.attr('data-temp-id', 'temp-' + (++tempIdCounter));
    }
    
    // Aggiorna ID in batch
    $newItem.find('input, select, textarea').each(function() {
        const $elem = $(this);
        const elemId = $elem.attr('id');
        
        if (elemId) {
            const newId = generateUniqueId(elemId.replace(/_[a-zA-Z0-9]+$/, ''));
            $elem.attr({
                'id': newId,
                'name': newId
            });
        }

        // Reset valori
        if ($elem.is('select')) {
            $elem.find('option:first').prop('selected', true);
        } else {
            $elem.val('');
        }
    });

    // Inizializza nested forms in batch
    $newItem.find('.nested-form-header').each(function() {
        const $header = $(this);
        const $toggleBtn = $header.find('.toggle-btn');
        const $collapseDiv = $header.next('.nested-form-container');
        
        const newId = generateUniqueId('nested_form');
        $toggleBtn.attr({
            'data-bs-target': '#' + newId,
            'aria-controls': newId
        });
        $collapseDiv.attr('id', newId);
    });

    // Inizializza struttura iniziale se necessario
    if (isInitialStructure) {
        $newItem.find('[data-repeater-list]').each(function() {
            const $nestedList = $(this);
            const minItems = parseInt($nestedList.data('min-items') || 0);
            
            if (minItems > 0) {
                const templateKey = $nestedList.data('repeater-list');

                // Check if template exists, if not create it from first item
                if (!initialCopies[templateKey]) {
                    const firstItem = $nestedList.find('[data-repeater-item]').first();
                    if (firstItem.length > 0) {
                        initialCopies[templateKey] = firstItem.clone(true, true);
                    } else {
                        console.warn('No template found for nested repeater:', templateKey);
                        return; // Skip this nested list if no template
                    }
                }

                const $template = initialCopies[templateKey].clone(true, true);

                for (let i = 0; i < minItems; i++) {
                    const $nestedItem = $template.clone(true, true);
                    initializeNewItem($nestedItem, true);
                    $nestedList.append($nestedItem);
                }
            }
        });
    }

    // Inizializza date inputs
    $newItem.find('.date-type-selector').each(function() {
        showAppropriateDateInput($(this));
    });

    setRequiredForVisibleFields($newItem, isInitialStructure);

    $newItem.find('input[data-supports-search="True"], textarea[data-supports-search="True"]').each(function() {
        enhanceInputWithSearch($(this));
    });
    
    // Apply top-level search for depth=0 inputs
    const entityType = $('#entity_type').val();
    if (entityType) {
        $newItem.find('input[data-depth="0"][data-supports-search="True"], textarea[data-depth="0"][data-supports-search="True"]').each(function() {
            enhanceTopLevelSearch($(this), entityType);
        });
    }
}

// Funzione ricorsiva per raccogliere i dati dai campi del form
function collectFormData(container, data, shacl, depth) {    
    if (shacl === 'True' || shacl === true) {
        container.find('[data-repeater-list]:visible').each(function() {
            let repeaterList = $(this);

            if (repeaterList.data('skip-collect')) {
                return;
            }

            let predicateUri = repeaterList.find('[data-repeater-item]:first').data('predicate-uri');
            let orderedBy = repeaterList.data('ordered-by');
            repeaterList.children('[data-repeater-item]:visible').each(function(index) {
                let repeaterItem = $(this);
                
                if (repeaterItem.data('skip-collect')) {
                    return;
                }
                
                let itemDepth = parseInt(repeaterItem.data('depth'));
                let objectClass = repeaterItem.find('[data-class]:visible').first().data('class');
                let tempId = repeaterItem.data('temp-id');
                let entityReference = repeaterItem.find('input[data-entity-reference="true"]');
                
                // Always process items at current depth to collect intermediate metadata
                if (predicateUri && objectClass && itemDepth === depth) {
                    let itemData = {};
                    let hasContent = false;
                    
                    if (repeaterItem.data('intermediate-relation')) {
                        let intermediateClass = repeaterItem.data('intermediate-relation');
                        let connectingProperty = repeaterItem.data('connecting-property');
                        let intermediateShape = repeaterItem.data('shape');
                        let targetEntityType = repeaterItem.data('target-entity-type');
                        let targetShape = repeaterItem.data('target-shape');
                        
                        let intermediateEntity = createIntermediateEntity(intermediateClass, intermediateShape, targetEntityType, targetShape);
                        
                        // Always collect nested properties first, regardless of entity references
                        let nestedShape = intermediateEntity.targetShape || repeaterItem.data('shape');
                        let nestedEntity = handleNestedProperties(
                            repeaterItem, 
                            objectClass, 
                            nestedShape, 
                            shacl, 
                            itemDepth + 1
                        );
                        
                        if (nestedEntity) {
                            intermediateEntity.properties[connectingProperty] = nestedEntity;
                            hasContent = true;
                        } else {
                            // If no nested entity, check for direct entity reference
                            let entityReferenceInput = repeaterItem.find('input[data-entity-reference="true"]');
                            if (entityReferenceInput.length > 0 && entityReferenceInput.val()) {
                                intermediateEntity.properties[connectingProperty] = [{
                                    is_existing_entity: true,
                                    entity_uri: entityReferenceInput.val()
                                }];
                                hasContent = true;
                            }
                        }

                        intermediateEntity = enrichEntityWithMetadata(
                            intermediateEntity, 
                            repeaterItem.data('additional-properties'), 
                            orderedBy, 
                            tempId
                        );

                        if (hasContent) {
                            itemData = intermediateEntity;
                        }
                    } else {
                        // Handle direct nested entities (not intermediate relations)
                        let nestedEntity = createIntermediateEntity(
                            objectClass, 
                            repeaterItem.data('shape')
                        );
                        
                        collectFormData(repeaterItem, nestedEntity.properties, shacl, itemDepth + 1);
                        
                        if (Object.keys(nestedEntity.properties).length > 0) {
                            nestedEntity = enrichEntityWithMetadata(nestedEntity, null, orderedBy, tempId);
                            itemData = nestedEntity;
                            hasContent = true;
                        } else {
                            // If no nested properties, check for entity reference
                            let nestedEntityReference = repeaterItem.find('input[data-entity-reference="true"]');
                            if (nestedEntityReference.length > 0 && nestedEntityReference.val()) {
                                itemData = {
                                    is_existing_entity: true,
                                    entity_uri: nestedEntityReference.val()
                                };
                                hasContent = true;
                            }
                        }
                    }

                    if (hasContent) {
                        ensurePropertyArray(data, predicateUri).push(itemData);
                    }
                } else if (itemDepth === depth) {
                    repeaterItem.find('input:visible, select:visible, input[data-mandatory-value="true"], textarea:visible').each(function() {
                        let propertyUri = $(this).data('predicate-uri');
                        if (propertyUri) {
                            let value = $(this).val() || $(this).data('value');
                            if (value !== "") {
                                ensurePropertyArray(data, propertyUri).push(value);
                            }
                        }
                    });
                }
            });
        });

        container.children('input:visible, select:visible, input[data-mandatory-value="true"], textarea:visible').each(function() {
            let propertyUri = $(this).data('predicate-uri');
            let inputDepth = parseInt($(this).data('depth'));
            if (propertyUri && inputDepth === depth) {
                let value = $(this).val();
                if (value !== "") {
                    ensurePropertyArray(data, propertyUri).push(value);
                }
            }
        });
        
        // Handle direct entity references not inside repeater lists
        container.find('input[data-entity-reference="true"]').each(function() {
            let entityReference = $(this);
            let refDepth = parseInt(entityReference.data('depth'));
            
            // Process references that are not already processed in repeater items
            // For entity references, we should collect them regardless of depth in edit mode
            const isInRepeaterItem = entityReference.closest('[data-repeater-item]').length > 0;
            
            if (!isInRepeaterItem) {
                // Determine if this reference is part of an intermediate relation
                let propertiesContainer = entityReference.closest('.newEntityPropertiesContainer');
                let predicateUri = entityReference.data('predicate-uri');
                let isPartOfIntermediateRelation = propertiesContainer.closest('[data-intermediate-relation]').length > 0;
                
                if (!predicateUri) {
                    // If predicate is not directly in the input, try to get it from container or nearest element
                    let closestRepeaterItem = propertiesContainer.closest('[data-repeater-item]');
                    if (closestRepeaterItem.length) {
                        predicateUri = closestRepeaterItem.data('predicate-uri');
                    }
                }
                
                if (predicateUri) {
                    let propArray = ensurePropertyArray(data, predicateUri);
                    
                    // If it's an intermediate relation, it might need a special structure
                    if (isPartOfIntermediateRelation) {
                        let intermediateContainer = propertiesContainer.closest('[data-intermediate-relation]');
                        let intermediateClass = intermediateContainer.data('intermediate-relation');
                        let connectingProperty = intermediateContainer.data('connecting-property');
                        let intermediateShape = intermediateContainer.data('shape');
                        let targetEntityType = intermediateContainer.data('target-entity-type');
                        let targetShape = intermediateContainer.data('target-shape');
                        
                        let intermediateEntity = createIntermediateEntity(intermediateClass, intermediateShape, targetEntityType, targetShape);
                        
                        let entityUri = entityReference.val();
                        if (entityUri) {
                            // Add explicit metadata for existing entity reference in intermediate relation
                            intermediateEntity.properties[connectingProperty] = [{
                                is_existing_entity: true,
                                entity_uri: entityUri
                            }];
                        }
                        
                        intermediateEntity = enrichEntityWithMetadata(
                            intermediateEntity, 
                            intermediateContainer.data('additional-properties'), 
                            null, 
                            null
                        );
                        
                        propArray.push(intermediateEntity);
                    } else {
                        let entityUri = entityReference.val();
                        if (entityUri) {
                            // Add explicit metadata for existing entity reference
                            propArray.push({
                                is_existing_entity: true,
                                entity_uri: entityUri
                            });
                        }
                    }
                }
            }
        });
    } else {
        $('.custom-property').each(function() {
            let propertyUri = $(this).find('input[type="url"]').val();
            let propertyValue = $(this).find('.custom-value-input').val();
            let valueType = $(this).find('.custom-value-type').val();
            let datatype = $(this).find('select[id^="custom_datatype_"]').val();

            if (propertyUri && propertyValue) {
                let propArray = ensurePropertyArray(data, propertyUri);
                
                if (valueType === 'uri') {
                    propArray.push({
                        value: propertyValue,
                        type: 'uri'
                    });
                } else {
                    propArray.push({
                        value: propertyValue,
                        type: 'literal',
                        datatype: datatype
                    });
                }
            }
        });
    }
    return data;
}

// Funzione per evidenziare i campi con errori
function highlightValidationErrors(errors) {
    // Rimuovi gli stati di errore precedenti
    $('.is-invalid').removeClass('is-invalid');
    $('.invalid-feedback').hide();

    errors.forEach(function(error) {
        if (error.field) {
            error.field.addClass('is-invalid');
            error.field.siblings('.invalid-feedback').first().text(error.message).show();
        }
    });
}

function validateUrl(url) {
    var pattern = new RegExp('^(https?:\\/\\/)?' + // protocollo
        '((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.?)+[a-z]{2,}|(\\d{1,3}\\.){3}\\d{1,3})' + // nome dominio e estensione
        '(\\:\\d+)?(\\/[-a-z\\d%_.~+]*)*' + // porta e percorso
        '(\\?[;&a-z\\d%_.~+=-]*)?' + // query string
        '(\\#[-a-z\\d_]*)?$', 'i'); // frammento
    return !!pattern.test(url);
}

function convertDate(originalValue, newType) {
    // Se l'originalValue è solo un anno o anno-mese, aggiungiamo valori di default
    if (/^\d{4}$/.test(originalValue)) {
        originalValue += '-01-01';
    } else if (/^\d{4}-\d{2}$/.test(originalValue)) {
        originalValue += '-01';
    }
    let date = new Date(originalValue);
    switch(newType) {
        case 'date':
            return date.toISOString().split('T')[0];
        case 'month':
            return date.toISOString().slice(0, 7);
        case 'year':
            return date.getFullYear().toString();
        default:
            return originalValue;
    }
}

$(document).ready(function() {
    // On change of date type selection
    $(document).on('change', '.date-type-selector', function() {
        let dateInputGroup = $(this).closest('.date-input-group');
        let originalValue = dateInputGroup.data('original-value');
        if (originalValue) {
            let newType = $(this).val();
            let newValue = convertDate(originalValue, newType);
            // Just set the value without triggering change events
            dateInputGroup.find(`.date-input[data-date-type="${newType}"]`).val(newValue);
            dateInputGroup.find('.date-display').text(newValue);
        }

        showAppropriateDateInput($(this));
    });

    // Initialize all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    $(document)
    .off('click.repeater', '[data-repeater-create]')
    .on('click.repeater', '[data-repeater-create]', function() {
        const $list = $(this).closest('[data-repeater-list]');
        const maxItems = parseInt($list.data('max-items')) || Infinity;
        const currentItems = $list.children('[data-repeater-item]').not('.repeater-template').length;
        
        if (currentItems >= maxItems) {
            return;
        }
    
        // Usa template dalla cache o creane uno nuovo
        const templateKey = $list.data('repeater-list');

        // Check if template exists, if not create it from first item
        if (!initialCopies[templateKey]) {
            const firstItem = $list.find('[data-repeater-item]').first();
            if (firstItem.length > 0) {
                initialCopies[templateKey] = firstItem.clone(true, true);
            } else {
                console.error('No template found for repeater:', templateKey);
                return;
            }
        }

        $template = initialCopies[templateKey].clone(true, true);
    
        const $newItem = $template.clone(true, true);
        $newItem.removeClass('d-none repeater-template');
    
        const isInitialStructure = $(this).hasClass('initial-structure-add');

        // Inserisci prima del pulsante "Add"
        $(this).before($newItem);

        // Inizializza il nuovo item
        initializeNewItem($newItem, isInitialStructure);
        
        // Aggiorna UI e binding
        const $newItemCollapse = $newItem.find('.collapse').addClass('show');
        $newItem.find('.toggle-btn').removeClass('collapsed');
    
        updateButtons($list, true);
        
        if ($list.data('ordered-by')) {
            updateSortable($list);
        }
        updateOrderedElementsNumbering();
    
        initializeMandatoryElements($newItem);
    
        // Inizializza i tooltip una sola volta per il nuovo item
        $newItem.find('[data-bs-toggle="tooltip"]').tooltip();
    });

    $(document)
        .off('click.repeaterDelete', '[data-repeater-delete]')
        .on('click.repeaterDelete', '[data-repeater-delete]', function() {
        const $list = $(this).closest('[data-repeater-list]');
        $(this).closest('[data-repeater-item]').remove();
        updateButtons($list);
        updateOrderedElementsNumbering();
        setRequiredForVisibleFields($list);
    });

    $(document)
        .off('shown.bs.collapse hidden.bs.collapse', '.collapse')
        .on('shown.bs.collapse hidden.bs.collapse', '.collapse', function(e) {
        e.stopPropagation();
        var $header = $(this).prev('.nested-form-header');
        $header.find('.toggle-btn').toggleClass('collapsed', e.type === 'hidden');
        
        // Aggiorniamo lo stato required per tutti gli elementi visibili dopo l'espansione/collasso
        setRequiredForVisibleFields($(this).closest('[data-repeater-list]'));
    });

    $(document).on('change', '.container-type-selector', async function() {
        const $container = $(this).closest('[data-repeater-item]');
        const $selectedOption = $(this).find('option:selected');
        const selectedShape = $selectedOption.data('node-shape');
        const selectedClass = $selectedOption.data('object-class');

        const $containerForms = $container.find('.container-forms');
        $container.find('.container-form').addClass('d-none');

        if (selectedShape) {
            $container.attr('data-skip-collect', 'true');
            $containerForms.removeClass('d-none');

            const $selectedForm = $container.find(`.container-form[data-shape="${selectedShape}"][data-class="${selectedClass}"]`);
            const needsLazyLoad = $selectedForm.attr('data-lazy-form-placeholder') === 'true' && $containerForms.data('lazy-load') === true;

            if (needsLazyLoad) {
                const depth = parseInt($containerForms.data('depth'));
                const predicateUri = $containerForms.data('predicate-uri');
                const $parentRepeaterList = $container.closest('[data-repeater-list]');
                const parentEntityClass = $parentRepeaterList.data('class');
                const parentEntityShape = $parentRepeaterList.data('subject-shape');

                try {
                    $selectedForm.html('<div class="text-center my-3"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></div>');
                    $selectedForm.removeClass('d-none');

                    const response = await fetch('/api/render-nested-form', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: JSON.stringify({
                            parent_entity_class: parentEntityClass,
                            parent_entity_shape: parentEntityShape,
                            entity_class: selectedClass,
                            entity_shape: selectedShape,
                            predicate_uri: predicateUri,
                            depth: depth,
                            is_template: false
                        })
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }

                    const html = await response.text();
                    $selectedForm.html(html);
                    $selectedForm.removeAttr('data-lazy-form-placeholder');

                    initializeMandatoryElements($selectedForm);
                    $selectedForm.find('[data-bs-toggle="tooltip"]').tooltip();
                    initializeRepeaters($selectedForm);

                } catch (error) {
                    console.error('Error loading nested form:', error);
                    $selectedForm.html(`<div class="alert alert-danger">${error.message}</div>`);
                }
            } else {
                $selectedForm.removeClass('d-none');
            }

            // Aggiorna gli attributi data del container con le informazioni dalla shape e classe selezionate
            $container
                .attr('data-object-class', selectedClass)
                .attr('data-target-class', $selectedOption.data('target-class'))
                .attr('data-node-shape', selectedShape);

            // Trova il pulsante "Add" per questa combinazione classe/shape e simulane il click
            const addButton = $selectedForm.find('[data-repeater-create]').not('.repeater-template').find('button.add-button').last();
            if (addButton.length) {
                // Verifica se non ci sono già elementi (escluso il template)
                const existingItems = $selectedForm
                    .find(`[data-repeater-list] [data-repeater-item][data-shape="${selectedShape}"][data-class="${selectedClass}"]`)
                    .not('.repeater-template')
                    .not('.d-none');

                if (existingItems.length === 0) {
                    addButton.click();
                }
            }

            // Inizializza gli elementi obbligatori del form selezionato
            if (!needsLazyLoad) {
                initializeMandatoryElements($selectedForm);
            }
        } else {
            // Se nessuna opzione è selezionata, nascondi il contenitore dei form
            $container.removeAttr('data-skip-collect');
            $containerForms.addClass('d-none');
        }
    });

    $(document).on({
        mouseenter: function() {
            $(this).closest('[data-repeater-item], .custom-property').addClass('highlight-delete');
        },
        mouseleave: function() {
            const $item = $(this).closest('[data-repeater-item], .custom-property');
            $item.removeClass('highlight-delete');
        }
    }, '.repeater-delete-btn, .delete-button, .remove-property');
});