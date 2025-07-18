// Store initial copies of repeater items
var initialCopies = {};

var pendingChanges = [];

var tempIdCounter = 0;

// Debouncing for form initialization
let initializeFormTimeout = null;

function generateUniqueId(prefix) {
    return prefix + '_' + Math.random().toString(36).substring(2, 11);
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
    console.log(`🔧 [DEBUG] initializeMandatoryElements called`);
    
    PerformanceDebugger.measure('enable_inputs', () => {
        container.find(':input').each(function() {
            $(this).prop('disabled', false);
        });
    });

    const repeaterLists = container.find('[data-repeater-list]');
    console.log(`📊 [DEBUG] Found ${repeaterLists.length} repeater lists`);
    
    PerformanceDebugger.measure('process_repeater_lists', () => {
        repeaterLists.each(function() {
            var list = $(this);
            var minItems = parseInt(list.data('min-items') || 0);
            var currentItems = list.children('[data-repeater-item]').not('.repeater-template').length;
            console.log(`📊 [DEBUG] List ${list.data('repeater-list')}: minItems=${minItems}, currentItems=${currentItems}`);
            
            if (minItems > 0 && currentItems === 0) {
                // Simulate click on add button for mandatory elements of the initial structure
                var addButton = list.find('[data-repeater-create] .initial-structure-add');
                console.log(`🔧 [DEBUG] Creating ${minItems} mandatory items for ${list.data('repeater-list')}`);
                for (var i = 0; i < minItems; i++) {
                    addButton.click();
                }
            }
        });
    });
}

// Batched version of initializeMandatoryElements for better performance
function initializeMandatoryElementsBatched(container) {
    console.log(`🔧 [DEBUG] initializeMandatoryElementsBatched called`);
    
    // Enable inputs in batch
    PerformanceDebugger.measure('enable_inputs_batched', () => {
        const inputs = container.find(':input').get();
        inputs.forEach(input => {
            input.disabled = false;
        });
    });

    const repeaterLists = container.find('[data-repeater-list]');
    console.log(`📊 [DEBUG] Found ${repeaterLists.length} repeater lists`);
    
    if (repeaterLists.length === 0) {
        return;
    }
    
    // Process repeater lists in batches using requestAnimationFrame
    const listsToProcess = [];
    repeaterLists.each(function() {
        const list = $(this);
        const minItems = parseInt(list.data('min-items') || 0);
        const currentItems = list.children('[data-repeater-item]').not('.repeater-template').length;
        
        if (minItems > 0 && currentItems === 0) {
            listsToProcess.push({
                list: list,
                minItems: minItems,
                addButton: list.find('[data-repeater-create] .initial-structure-add')
            });
        }
    });
    
    if (listsToProcess.length === 0) {
        return;
    }
    
    // Process lists in chunks to avoid blocking the UI
    let currentListIndex = 0;
    
    function processBatch() {
        const startTime = performance.now();
        
        // Process up to 3 lists or until we've used 16ms (60fps frame budget)
        let processedCount = 0;
        while (currentListIndex < listsToProcess.length && 
               processedCount < 3 && 
               (performance.now() - startTime) < 16) {
            
            const listInfo = listsToProcess[currentListIndex];
            console.log(`🔧 [DEBUG] Creating ${listInfo.minItems} mandatory items for ${listInfo.list.data('repeater-list')}`);
            
            // Create items in a batch
            for (let i = 0; i < listInfo.minItems; i++) {
                listInfo.addButton.click();
            }
            
            currentListIndex++;
            processedCount++;
        }
        
        // If there are more lists to process, schedule next batch
        if (currentListIndex < listsToProcess.length) {
            requestAnimationFrame(processBatch);
        }
    }
    
    // Start processing
    requestAnimationFrame(processBatch);
}

// Performance debugging utilities
const PerformanceDebugger = {
    timers: new Map(),
    
    start(label) {
        this.timers.set(label, performance.now());
        console.log(`🟡 [PERF] Started: ${label}`);
    },
    
    end(label) {
        const startTime = this.timers.get(label);
        if (startTime) {
            const duration = performance.now() - startTime;
            console.log(`🟢 [PERF] Finished: ${label} - ${duration.toFixed(2)}ms`);
            this.timers.delete(label);
            return duration;
        }
        return 0;
    },
    
    measure(label, fn) {
        this.start(label);
        const result = fn();
        this.end(label);
        return result;
    }
};

function initializeForm() {
    PerformanceDebugger.start('initializeForm_total');
    let selectedUri;
    let selectedShape;
    if ($('#entity_type').length) {
        const selectedOption = $('#entity_type option:selected');
        
        // Se l'opzione selezionata è quella predefinita (disabled) o non è selezionata alcuna opzione
        if (selectedOption.is(':disabled') || !selectedOption.val()) {
            // Seleziona automaticamente la prima opzione non disabilitata
            const firstOption = $('#entity_type option:not(:disabled):first');
            if (firstOption.length) {
                selectedUri = firstOption.val();
                selectedShape = firstOption.data('shape');
                $('#entity_type').val(selectedUri);
            } else {
                selectedUri = null;
                selectedShape = null;
            }
        } else {
            // Ottieni i valori dall'opzione selezionata
            selectedUri = selectedOption.val();
            selectedShape = selectedOption.data('shape');
        }
    } else if (typeof entity_type !== 'undefined' && entity_type) {
        // In about.jinja, use the entity_type variable
        selectedUri = entity_type;
    }

    if (selectedUri) {
        console.log(`🔍 [DEBUG] Processing entity: ${selectedUri}, shape: ${selectedShape}`);
        
        // Cache jQuery objects to avoid repeated selections
        const $propertyGroups = $('.property-group');
        
        // Hide all property groups
        PerformanceDebugger.measure('hide_property_groups', () => {
            $propertyGroups.hide();
        });

        // Count total property groups for debugging
        const totalGroups = $propertyGroups.length;
        console.log(`📊 [DEBUG] Total property groups: ${totalGroups}`);
        
        // Find matching property group
        let selectedGroup = null;
        let classMatch = null;
        let shapeMatch = null;
        
        const matchingTime = PerformanceDebugger.measure('find_matching_group', () => {
            // Cerca tutti i gruppi di proprietà disponibili
            $propertyGroups.each(function() {
                const $this = $(this);
                const groupUri = $this.data('uri');
                const groupShape = $this.data('shape');
                
                // Caso 1: Corrispondenza esatta sia per classe che per shape
                if (selectedUri && selectedShape && 
                    groupUri === selectedUri && 
                    groupShape === selectedShape) {
                    // La corrispondenza esatta ha sempre la precedenza più alta
                    selectedGroup = $this;
                    console.log(`✅ [DEBUG] Found exact match: ${groupUri} + ${groupShape}`);
                    return false; // Interrompe il ciclo each
                }
                
                // Caso 2: Solo la classe corrisponde
                if (selectedUri && groupUri === selectedUri && !groupShape) {
                    classMatch = $this;
                    console.log(`⚠️ [DEBUG] Found class match: ${groupUri}`);
                }
                
                // Caso 3: Solo lo shape corrisponde
                if (selectedShape && groupShape === selectedShape && !groupUri) {
                    shapeMatch = $this;
                    console.log(`⚠️ [DEBUG] Found shape match: ${groupShape}`);
                }
            });
        });
        
        // Se non abbiamo trovato una corrispondenza esatta, usa la migliore disponibile
        // Le regole shape hanno tipicamente una specificità più alta, quindi le preferiamo
        if (!selectedGroup) {
            selectedGroup = shapeMatch || classMatch;
        }
        
        // Mostra solo il gruppo selezionato
        if (selectedGroup && selectedGroup.length > 0) {
            PerformanceDebugger.measure('show_selected_group', () => {
                selectedGroup.show();
            });
            
            // Count elements in selected group for debugging
            const elementsInGroup = selectedGroup.find('*').length;
            console.log(`📊 [DEBUG] Elements in selected group: ${elementsInGroup}`);
            
            // Initialize mandatory elements with batching and debouncing
            PerformanceDebugger.measure('initialize_mandatory_elements', () => {
                initializeMandatoryElementsBatched(selectedGroup);
            });
        } else {
            console.log(`❌ [DEBUG] Nessun gruppo di proprietà trovato per URI=${selectedUri}${selectedShape ? ' e shape=' + selectedShape : ''}`);
        }
    } else {
        // Se non è selezionato alcun tipo, disabilita tutti gli input
        PerformanceDebugger.measure('disable_inputs', () => {
            $('.property-group :input').prop('disabled', true);
        });
    }
    
    const totalTime = PerformanceDebugger.end('initializeForm_total');
    console.log(`🎯 [PERF] initializeForm total time: ${totalTime.toFixed(2)}ms`);
}

// Debounced version of initializeForm
function initializeFormDebounced() {
    // Clear any existing timeout
    if (initializeFormTimeout) {
        clearTimeout(initializeFormTimeout);
    }
    
    // Set a new timeout
    initializeFormTimeout = setTimeout(() => {
        initializeForm();
        initializeFormTimeout = null;
    }, 50); // 50ms delay to prevent rapid successive calls
}

function storePendingChange(action, subject, predicate, object, newObject = null, shape = null, entity_type = null) {
    pendingChanges.push({
        action: action, 
        subject: subject, 
        predicate: predicate, 
        object: object, 
        newObject: newObject,
        shape: shape,
        entity_type: entity_type
    });
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
            $(evt.from).find('.property-value').each(function() {
                const objectId = $(this).data('old-object-id');
                const tempId = $(this).data('temp-id');
                if (objectId) {
                    new_order.push(objectId);
                } else if (tempId) {
                    new_order.push(tempId);
                }
                predicate = $(this).data('property-id');
                orderedBy = $(this).data('ordered_by');
                shape = $(this).data('shape');
            });
            updateOrderedElementsNumbering();

            if (typeof subject === 'undefined' || subject === 'null' || subject === null) {
                return;
            }

            // Cerca un'azione di ordinamento esistente per questo predicato
            let existingOrderIndex = pendingChanges.findIndex(change => 
                change.action === 'order' && 
                change.predicate === predicate
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
    console.log(`🔧 [DEBUG] initializeNewItem called, isInitialStructure=${isInitialStructure}`);
    PerformanceDebugger.start('initializeNewItem_total');
    
    $newItem.addClass('added-in-edit-mode');

    if ($newItem.hasClass('draggable')) {
        $newItem.attr('data-temp-id', 'temp-' + (++tempIdCounter));
    }
    
    // Batch DOM operations by collecting all elements first
    const inputs = $newItem.find('input, select, textarea').get();
    const nestedHeaders = $newItem.find('.nested-form-header').get();
    const dateSelectors = $newItem.find('.date-type-selector').get();
    const searchInputs = $newItem.find('input[data-supports-search="True"], textarea[data-supports-search="True"]').get();
    
    // Aggiorna ID in batch
    PerformanceDebugger.measure('update_ids', () => {
        inputs.forEach(elem => {
            const $elem = $(elem);
            const elemId = $elem.attr('id');
            
            if (elemId) {
                const newId = generateUniqueId(elemId.replace(/_[a-zA-Z0-9]+$/, ''));
                elem.id = newId;
                elem.name = newId;
            }

            // Reset valori
            if (elem.tagName === 'SELECT') {
                elem.selectedIndex = 0;
            } else {
                elem.value = '';
            }
        });
    });

    // Inizializza nested forms in batch
    PerformanceDebugger.measure('initialize_nested_forms', () => {
        nestedHeaders.forEach(header => {
            const $header = $(header);
            const $toggleBtn = $header.find('.toggle-btn');
            const $collapseDiv = $header.next('.nested-form-container');
            
            const newId = generateUniqueId('nested_form');
            $toggleBtn.attr({
                'data-bs-target': '#' + newId,
                'aria-controls': newId
            });
            $collapseDiv.attr('id', newId);
        });
    });

    // Inizializza struttura iniziale se necessario (defer to avoid blocking)
    if (isInitialStructure) {
        PerformanceDebugger.measure('initialize_initial_structure', () => {
            const nestedLists = $newItem.find('[data-repeater-list]').get();
            
            // Process nested lists in smaller batches
            nestedLists.forEach(nestedList => {
                const $nestedList = $(nestedList);
                const minItems = parseInt($nestedList.data('min-items') || 0);
                
                if (minItems > 0) {
                    const templateKey = $nestedList.data('repeater-list');
                    const $template = initialCopies[templateKey].clone(true, true);
                    
                    console.log(`🔧 [DEBUG] Creating ${minItems} nested items for ${templateKey}`);
                    for (let i = 0; i < minItems; i++) {
                        const $nestedItem = $template.clone(true, true);
                        initializeNewItem($nestedItem, true);
                        $nestedList.append($nestedItem);
                    }
                }
            });
        });
    }

    // Inizializza date inputs
    PerformanceDebugger.measure('initialize_date_inputs', () => {
        dateSelectors.forEach(selector => {
            showAppropriateDateInput($(selector));
        });
    });

    PerformanceDebugger.measure('set_required_fields', () => {
        setRequiredForVisibleFields($newItem, isInitialStructure);
    });

    PerformanceDebugger.measure('enhance_search_inputs', () => {
        searchInputs.forEach(input => {
            enhanceInputWithSearch($(input));
        });
        
        // Apply top-level search for depth=0 inputs
        const entityType = $('#entity_type').val();
        if (entityType) {
            const topLevelSearchInputs = $newItem.find('input[data-depth="0"][data-supports-search="True"], textarea[data-depth="0"][data-supports-search="True"]').get();
            topLevelSearchInputs.forEach(input => {
                enhanceTopLevelSearch($(input), entityType);
            });
        }
    });
    
    const totalTime = PerformanceDebugger.end('initializeNewItem_total');
    console.log(`🎯 [PERF] initializeNewItem total time: ${totalTime.toFixed(2)}ms`);
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
            repeaterList.children('[data-repeater-item]:visible').each(function() {
                let repeaterItem = $(this);
                
                if (repeaterItem.data('skip-collect')) {
                    return;
                }
                
                let itemDepth = parseInt(repeaterItem.data('depth'));
                let objectClass = repeaterItem.find('[data-class]:visible').first().data('class');
                let tempId = repeaterItem.data('temp-id');
                let entityReference = repeaterItem.find('input[data-entity-reference="true"]');
                
                if (predicateUri && objectClass && itemDepth === depth) {
                    let itemData = {};
                    let hasContent = false;
                    
                    // Handle direct entity reference at current depth
                    if (entityReference.length > 0 && parseInt(entityReference.data('depth')) === depth) {
                        // Se non è una relazione intermedia, gestisci come riferimento diretto
                        if (!repeaterItem.data('intermediate-relation')) {
                            let entityUri = entityReference.val();
                            if (entityUri) {
                                // Add explicit metadata for existing entity reference
                                ensurePropertyArray(data, predicateUri).push({
                                    is_existing_entity: true,
                                    entity_uri: entityUri
                                });
                            }
                            return;
                        }
                        // Altrimenti, lascia che sia gestito dal blocco delle relazioni intermedie sotto
                    }
                    
                    if (repeaterItem.data('intermediate-relation')) {
                        let intermediateClass = repeaterItem.data('intermediate-relation');
                        let connectingProperty = repeaterItem.data('connecting-property');
                        let intermediateShape = repeaterItem.data('shape');
                        let targetEntityType = repeaterItem.data('target-entity-type');
                        let targetShape = repeaterItem.data('target-shape');
                        
                        let intermediateEntity = createIntermediateEntity(intermediateClass, intermediateShape, targetEntityType, targetShape);
                        
                        let entityReferenceInput = repeaterItem.find('input[data-entity-reference="true"]');
                        let isDirectReference = false;
                        let directReferenceValue = null;
                        
                        if (entityReferenceInput.length > 0 && 
                            parseInt(entityReferenceInput.data('depth')) === itemDepth + 1) {
                            
                            isDirectReference = true;
                            directReferenceValue = entityReferenceInput.val();
                        }
                        
                        if (isDirectReference && directReferenceValue) {
                            // Add explicit metadata for existing entity reference in intermediate relation
                            intermediateEntity.properties[connectingProperty] = [{
                                is_existing_entity: true,
                                entity_uri: directReferenceValue
                            }];
                            hasContent = true;
                        } else {
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
                        let nestedEntityReference = repeaterItem.find('input[data-entity-reference="true"]');
                        if (nestedEntityReference.length > 0 && 
                            parseInt(nestedEntityReference.data('depth')) === depth + 1) {
                            
                            let entityUri = nestedEntityReference.val();
                            if (entityUri) {
                                // Add explicit metadata for existing entity reference
                                itemData = {
                                    is_existing_entity: true,
                                    entity_uri: entityUri
                                };
                                hasContent = true;
                            }
                        } else {
                            let nestedEntity = createIntermediateEntity(
                                objectClass, 
                                repeaterItem.data('shape')
                            );
                            
                            collectFormData(repeaterItem, nestedEntity.properties, shacl, itemDepth + 1);
                            
                            if (Object.keys(nestedEntity.properties).length > 0) {
                                nestedEntity = enrichEntityWithMetadata(nestedEntity, null, orderedBy, tempId);
                                
                                itemData = nestedEntity;
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
            
            // Process only references at current depth that are not already processed in repeater items
            if (refDepth === depth && !entityReference.closest('[data-repeater-item]').length) {
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

$('[data-repeater-list]').each(function() {
    var list = $(this);
    var firstItem = list.find('[data-repeater-item]').first();
    initialCopies[list.data('repeater-list')] = firstItem.clone(true, true);

     // Initialize Sortable for each repeater list
    if (list.data('ordered-by')) {
        updateSortable(list);
    }
});

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
            dateInputGroup.find(`.date-input[data-date-type="${newType}"]`).val(newValue);
            dateInputGroup.find('.date-display').text(newValue);    
        }

        showAppropriateDateInput($(this));
    });

    // Initialize all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
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

        $template = initialCopies[templateKey].clone(true, true);
    
        const $newItem = $template.clone(true, true);
        $newItem.removeClass('d-none repeater-template');
    
        const isInitialStructure = $(this).hasClass('initial-structure-add');

        // Inserisci prima del pulsante "Add"
        $(this).before($newItem);

        // Inizializza il nuovo item
        initializeNewItem($newItem, isInitialStructure);
        
        // Aggiorna UI e binding
        $newItem.find('.collapse').addClass('show');
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

    $(document).on('change', '.container-type-selector', function() {
        const $container = $(this).closest('[data-repeater-item]');
        const $selectedOption = $(this).find('option:selected');
        const selectedShape = $selectedOption.data('node-shape');
        const selectedClass = $selectedOption.data('object-class');

        const $containerForms = $container.find('.container-forms');
        $container.find('.container-form').addClass('d-none');
        
        // Imposta l'attributo data-skip-collect="true" quando viene selezionato un valore
        if (selectedShape) {
            $container.attr('data-skip-collect', 'true');
            $containerForms.removeClass('d-none');
            
            // Trova il form corrispondente alla classe e shape selezionate
            const $selectedForm = $container.find(`.container-form[data-shape="${selectedShape}"][data-class="${selectedClass}"]`);
            $selectedForm.removeClass('d-none');

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
            initializeMandatoryElements($selectedForm);
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