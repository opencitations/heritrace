// Store initial copies of repeater items
var initialCopies = {};

var pendingChanges = [];

var tempIdCounter = 0;

function generateUniqueId(prefix) {
    return prefix + '_' + Math.random().toString(36).substr(2, 9);
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
    container.find(':input').each(function() {
        $(this).prop('disabled', false);
    });

    container.find('[data-repeater-list]').each(function() {
        var list = $(this);
        var minItems = parseInt(list.data('min-items') || 0);
        var currentItems = list.children('[data-repeater-item]').not('.repeater-template').length;
        if (minItems > 0 && currentItems === 0) {
            // Simulate click on add button for mandatory elements of the initial structure
            var addButton = list.find('[data-repeater-create] .initial-structure-add');
            for (var i = 0; i < minItems; i++) {
                addButton.click();
            }
        }
    });
}

// Function to initialize the form based on the selected entity type
function initializeForm() {
    let selectedUri;
    if ($('#entity_type').length) {
        // In create_entity.jinja
        selectedUri = $('#entity_type').val();
        $('#entity_type option').prop('selected', function() {
            return this.value === selectedUri;
        });
    } else if (typeof entity_type !== 'undefined' && entity_type) {
        // In about.jinja, use the entity_type variable
        selectedUri = entity_type;
    }

    if (selectedUri) {
        // Hide all property groups
        $('.property-group').hide();

        // Show the selected group
        let selectedGroup = $(`.property-group[data-uri="${selectedUri}"]`);
        selectedGroup.show();
        
        // Initialize mandatory elements recursively
        initializeMandatoryElements(selectedGroup);
    } else {
        // If no type is selected, disable all inputs
        $('.property-group :input').prop('disabled', true);
    }
}

function storePendingChange(action, subject, predicate, object, newObject = null, shape = null) {
    pendingChanges.push({
        action: action, 
        subject: subject, 
        predicate: predicate, 
        object: object, 
        newObject: newObject,
        shape: shape
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
                new_order.push($(this).data('old-object-id'));
                predicate = $(this).data('property-id');
                orderedBy = $(this).data('ordered_by');
                shape = $(this).data('shape');
            });
            updateOrderedElementsNumbering();

            if (typeof subject === 'undefined' || subject === 'null' || subject === null) {
                return;
            }

            // Cerca un'azione di ordinamento esistente per questo predicato e forma
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
                storePendingChange('order', subject, predicate, new_order, orderedBy, shape);
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

    $newItem.find('input').each(function() {
        enhanceInputWithSearch($(this));
    });
}

// Funzione ricorsiva per raccogliere i dati dai campi del form
function collectFormData(container, data, shacl = 'False', depth = 0) {
    if (shacl === 'True' || shacl === true) {
        container.find('[data-repeater-list]').each(function() {
            let repeaterList = $(this);
            let predicateUri = repeaterList.find('[data-repeater-item]:first').data('predicate-uri');
            let orderedBy = repeaterList.data('ordered-by');

            repeaterList.find('[data-repeater-item]:visible').each(function(index) {
                let repeaterItem = $(this);
                let objectClass = repeaterItem.find('[data-object-class]:visible').first().data('object-class');
                let itemDepth = parseInt(repeaterItem.data('depth'));
                let tempId = repeaterItem.data('temp-id');

                // Check if this item contains a reference to an existing entity
                let entityReference = repeaterItem.find('input[data-entity-reference="true"]');
                if (entityReference.length > 0) {
                    // Se siamo in una relazione intermedia
                    if (repeaterItem.data('intermediate-relation')) {
                        let intermediateClass = repeaterItem.data('intermediate-relation');
                        let connectingProperty = repeaterItem.data('connecting-property');
                        
                        // Creiamo la struttura dell'entità intermedia
                        let intermediateEntity = {
                            "entity_type": intermediateClass,
                            "properties": {}
                        };

                        // Aggiungiamo la connessione all'entità esistente
                        intermediateEntity.properties[connectingProperty] = entityReference.val();

                        let intermediateShape = repeaterItem.data('shape');
                        if (intermediateShape) {
                            intermediateEntity['shape'] = intermediateShape;
                        }

                        // Aggiungiamo eventuali proprietà aggiuntive
                        let additionalProperties = repeaterItem.data('additional-properties');
                        if (additionalProperties) {
                            Object.assign(intermediateEntity.properties, additionalProperties);
                        }

                        if (orderedBy) {
                            intermediateEntity['orderedBy'] = orderedBy;
                        }

                        if (tempId) {
                            intermediateEntity['tempId'] = tempId;
                        }

                        // Aggiungiamo l'entità intermedia alla lista delle proprietà
                        if (!data[predicateUri]) {
                            data[predicateUri] = [];
                        }
                        data[predicateUri].push(intermediateEntity);
                    } else {
                        // Comportamento standard per riferimenti diretti
                        if (!data[predicateUri]) {
                            data[predicateUri] = [];
                        }
                        data[predicateUri].push(entityReference.val());
                    }
                    return;
                }

                if (predicateUri && objectClass && itemDepth === depth) {
                    let itemData = {};
                    let hasContent = false;

                    if (repeaterItem.data('intermediate-relation')) {
                        let intermediateClass = repeaterItem.data('intermediate-relation');
                        let connectingProperty = repeaterItem.data('connecting-property');
                        let intermediateEntity = {
                            "entity_type": intermediateClass,
                            "properties": {}
                        };

                        let intermediateShape = repeaterItem.data('shape');
                        if (intermediateShape) {
                            intermediateEntity['shape'] = intermediateShape;
                        }

                        let nestedProperties = {};
                        collectFormData(repeaterItem, nestedProperties, shacl, depth + 1);

                        if (Object.keys(nestedProperties).length > 0) {
                            intermediateEntity.properties[connectingProperty] = {
                                "entity_type": objectClass,
                                "properties": nestedProperties
                            };

                            let nestedShape = repeaterItem.find('[data-object-class]:visible').first().data('shape');
                            if (nestedShape) {
                                intermediateEntity.properties[connectingProperty]['shape'] = nestedShape;
                            }

                            hasContent = true;
                        }

                        let additionalProperties = repeaterItem.data('additional-properties');
                        if (additionalProperties) {
                            Object.assign(intermediateEntity.properties, additionalProperties);
                        }

                        if (orderedBy) {
                            intermediateEntity['orderedBy'] = orderedBy;
                        }

                        if (tempId) {
                            intermediateEntity['tempId'] = tempId;
                        }

                        if (hasContent) {
                            itemData = intermediateEntity;
                        }
                    } else {
                        let nestedEntity = {
                            "entity_type": objectClass,
                            "properties": {}
                        };

                        let nestedShape = repeaterItem.data('shape');
                        if (nestedShape) {
                            nestedEntity['shape'] = nestedShape;
                        }

                        collectFormData(repeaterItem, nestedEntity.properties, shacl, depth + 1);

                        if (orderedBy) {
                            nestedEntity['orderedBy'] = orderedBy;
                        }

                        if (tempId) {
                            nestedEntity['tempId'] = tempId;
                        }

                        if (Object.keys(nestedEntity.properties).length > 0) {
                            itemData = nestedEntity;
                            hasContent = true;
                        }
                    }

                    if (hasContent) {
                        if (!Array.isArray(data[predicateUri])) {
                            data[predicateUri] = [];
                        }
                        data[predicateUri].push(itemData);
                    }
                } else if (itemDepth === depth) {
                    repeaterItem.find('input:visible, select:visible, input[data-mandatory-value="true"], textarea:visible').each(function() {
                        let propertyUri = $(this).data('predicate-uri');
                        if (propertyUri) {
                            let value = $(this).val() || $(this).data('value');
                            if (value !== "") {
                                if (!data[propertyUri]) {
                                    data[propertyUri] = [];
                                }
                                data[propertyUri].push(value);
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
                    if (!data[propertyUri]) {
                        data[propertyUri] = [];
                    }
                    data[propertyUri].push(value);
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
                if (!data[propertyUri]) {
                    data[propertyUri] = [];
                }
                if (valueType === 'uri') {
                    data[propertyUri].push({
                        value: propertyValue,
                        type: 'uri'
                    });
                } else {
                    data[propertyUri].push({
                        value: propertyValue,
                        type: 'literal',
                        datatype: datatype
                    });
                }
            }
        });
    }
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

    $(document).on('change', '.container-type-selector', function() {
        const $container = $(this).closest('[data-repeater-item]');
        const $selectedOption = $(this).find('option:selected');
        const selectedShape = $selectedOption.val();
        const $containerForms = $container.find('.container-forms');
        $container.find('.container-form').addClass('d-none');
        if (selectedShape) {
            $containerForms.removeClass('d-none');
            const $selectedForm = $container.find(`.container-form[data-shape="${selectedShape}"]`);
            $selectedForm.removeClass('d-none');

            // Aggiorna gli attributi data del container con le informazioni dalla shape selezionata
            $container
                .attr('data-object-class', $selectedOption.data('object-class'))
                .attr('data-target-class', $selectedOption.data('target-class'))
                .attr('data-node-shape', $selectedOption.data('node-shape'));

            // Trova il pulsante "Add" per questa shape e simulane il click
            const addButton = $selectedForm.find('[data-repeater-create]').not('.repeater-template').find('button.add-button').last();
            if (addButton.length) {
                // Verifica se non ci sono già elementi (escluso il template)
                const existingItems = $selectedForm
                    .find(`[data-repeater-list] [data-repeater-item][data-shape="${selectedShape}"]`)
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
            $containerForms.addClass('d-none');
        }
    });

    $(document).on({
        mouseenter: function() {
            $(this).closest('[data-repeater-item]').addClass('highlight-delete');
        },
        mouseleave: function() {
            const $item = $(this).closest('[data-repeater-item]');
            $item.removeClass('highlight-delete');
        }
    }, '.repeater-delete-btn, .delete-button');
});