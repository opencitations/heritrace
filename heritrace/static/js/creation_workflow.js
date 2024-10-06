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
        
        // Enable inputs only in the selected group
        $('.property-group').each(function() {
            let group = $(this);
            let isSelected = group.data('uri') === selectedUri;
            group.find(':input').prop('disabled', !isSelected);
        });

        // Initialize mandatory elements of the initial structure
        selectedGroup.find('[data-repeater-list]').each(function() {
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
        var parentRepeaterList = elem.closest('[data-repeater-list]');
        var isRequired = parentRepeaterList.length > 0 && 
                        (isInitialStructure || parseInt(parentRepeaterList.data('min-items') || 0) > 0);
        elem.prop('required', isVisible && isRequired);
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

function bindRepeaterEvents(context) {
    function initializeNewItem(newItem, isRequired, isInitialStructure = false) {
        if (newItem.hasClass('draggable')) {
            var tempId = 'temp-' + (++tempIdCounter);
            newItem.attr('data-temp-id', tempId);
        }
        
        newItem.find('input, select, textarea').each(function() {
            var elem = $(this);
            var elemId = elem.attr('id');
            
            if (elemId) {
                var newId = generateUniqueId(elemId.replace(/_[a-zA-Z0-9]+$/, ''));
                elem.attr('id', newId);
                elem.attr('name', newId);
            }

            if (elem.is('select')) {
                elem.find('option:first').prop('selected', true);
            } else {
                elem.val('');
            }
        });

        newItem.find('.nested-form-header').each(function() {
            var $header = $(this);
            var $toggleBtn = $header.find('.toggle-btn');
            var $collapseDiv = $header.next('.nested-form-container');
            
            var newId = generateUniqueId('nested_form');
            $toggleBtn.attr('data-bs-target', '#' + newId);
            $toggleBtn.attr('aria-controls', newId);
            $collapseDiv.attr('id', newId);

            $collapseDiv.collapse({toggle: false});
        });

        // Inizializza gli elementi obbligatori della struttura iniziale
        if (isInitialStructure) {
            newItem.find('[data-repeater-list]').each(function() {
                var nestedList = $(this);
                var minItems = parseInt(nestedList.data('min-items') || 0);
                if (minItems > 0) {
                    for (var i = 0; i < minItems; i++) {
                        var nestedItem = initialCopies[nestedList.data('repeater-list')].clone(true, true);
                        initializeNewItem(nestedItem, true, true);
                        nestedItem.appendTo(nestedList);
                    }
                }
            });
        }

        newItem.find('.date-type-selector').each(function() {
            showAppropriateDateInput($(this));
        });
    }

    context.find('[data-repeater-create]').off('click').on('click', function() {
        var list = $(this).closest('[data-repeater-list]');
        var maxItems = parseInt(list.data('max-items')) || Infinity;
        var counter = list.children('[data-repeater-item]').not('.repeater-template').length;
        if (counter < maxItems) {
            var newItem = initialCopies[list.data('repeater-list')].clone(true, true);
            newItem.removeClass('d-none repeater-template');

            var isRequired = parseInt(list.data('min-items') || 0) > 0;
            var isInitialStructure = $(this).hasClass('initial-structure-add');

            initializeNewItem(newItem, isRequired, isInitialStructure);

            newItem.appendTo(list);
            list.children('[data-repeater-create]').appendTo(list);

            newItem.find('.collapse').addClass('show');
            newItem.find('.toggle-btn').removeClass('collapsed');

            updateButtons(list, true);

            if (list.data('ordered-by')) {
                updateSortable(list);
            }
            updateOrderedElementsNumbering();

            bindRepeaterEvents(newItem);

            setRequiredForVisibleFields(newItem, isInitialStructure);

            initializeForm();
        }
    });

    context.find('[data-repeater-delete]').off('click').on('click', function() {
        var list = $(this).closest('[data-repeater-list]');
        $(this).closest('[data-repeater-item]').remove();
        updateButtons(list);
        // Dopo aver rimosso un elemento, aggiorna la numerazione
        updateOrderedElementsNumbering();
        setRequiredForVisibleFields(list);
    });

    context.find('.collapse').on('shown.bs.collapse hidden.bs.collapse', function(e) {
        e.stopPropagation();
        var $header = $(this).prev('.nested-form-header');
        $header.find('.toggle-btn').toggleClass('collapsed', e.type === 'hidden');
        
        // Aggiorniamo lo stato required per tutti gli elementi visibili dopo l'espansione/collasso
        setRequiredForVisibleFields($(this).closest('[data-repeater-list]'));
    });

    setRequiredForVisibleFields(context);
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
        
                if (predicateUri && objectClass && itemDepth === depth) {
                    if (!Array.isArray(data[predicateUri])) {
                        data[predicateUri] = [];
                    }

                    if (repeaterItem.data('intermediate-relation')) {
                        let intermediateClass = repeaterItem.data('intermediate-relation');
                        let connectingProperty = repeaterItem.data('connecting-property');
                        let intermediateEntity = {
                            "entity_type": intermediateClass,
                            "properties": {}
                        };

                        // Aggiungi l'informazione sulla shape se disponibile
                        let intermediateShape = repeaterItem.data('shape');
                        if (intermediateShape) {
                            intermediateEntity['shape'] = intermediateShape;
                        }

                        intermediateEntity.properties[connectingProperty] = {
                            "entity_type": objectClass,
                            "properties": {}
                        };

                        // Aggiungi l'informazione sulla shape all'entità annidata se disponibile
                        let nestedShape = repeaterItem.find('[data-object-class]:visible').first().data('shape');
                        if (nestedShape) {
                            intermediateEntity.properties[connectingProperty]['shape'] = nestedShape;
                        }

                        let additionalProperties = repeaterItem.data('additional-properties');
                        if (additionalProperties) {
                            Object.assign(intermediateEntity.properties, additionalProperties);
                        }

                        collectFormData(repeaterItem, intermediateEntity.properties[connectingProperty].properties, shacl, depth + 1);
                        
                        if (orderedBy) {
                            intermediateEntity['orderedBy'] = orderedBy;
                        }

                        if (tempId) {
                            intermediateEntity['tempId'] = tempId;
                        }
        
                        data[predicateUri].push(intermediateEntity);
                    } else {
                        let nestedEntity = {
                            "entity_type": objectClass,
                            "properties": {}
                        };

                        // Aggiungi l'informazione sulla shape se disponibile
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
                            data[predicateUri].push(nestedEntity);
                        }
                    }
                } else if (itemDepth === depth) {
                    repeaterItem.find('input:visible, select:visible').each(function() {
                        let propertyUri = $(this).data('predicate-uri');
                        if (propertyUri) {
                            let value = $(this).val();
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

        container.children('input:visible, select:visible').each(function() {
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

// Funzione per validare i campi richiesti
function validateRequiredFields(errors) {
    $(':input[required]:visible').each(function() {
        if (!$(this).val()) {
            let fieldName = $(this).closest('.form-floating').find('label').text() || 
                            $(this).attr('placeholder') || 
                            $(this).attr('name') || 
                            '{{ _("Unknown field") }}';
            errors.push({
                field: $(this),
                message: `{{ _("The field") }} "${fieldName}" {{ _("is required") }}`
            });
        }
    });
}

// Funzione per validare gli URL
function validateUrls(errors) {
    $('input[type="url"]:visible').each(function() {
        let url = $(this).val();
        if (url && !validateUrl(url)) {
            let fieldName = $(this).closest('.form-floating').find('label').text() || 
                            $(this).attr('placeholder') || 
                            $(this).attr('name') || 
                            '{{ _("Unknown URL field") }}';
            errors.push({
                field: $(this),
                message: `{{ _("Please enter a valid URL for") }} "${fieldName}"`
            });
        }
    });
}

// Funzione per validare i campi in base al datatype
function validateDatatypes(errors) {
    $('[data-datatypes]:visible').each(function() {
        let input = $(this);
        let datatypes = input.data('datatypes').split(',');
        let value = input.val();
        let isValidDatatype = false;
        let expectedFormat = '';

        datatypes.forEach(function(datatype) {
            switch(datatype) {
                case 'http://www.w3.org/2001/XMLSchema#string':
                    isValidDatatype = true; // All strings are valid
                    expectedFormat = '{{ _("any text") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#normalizedString':
                    isValidDatatype = !/[\n\r\t]/.test(value);
                    expectedFormat = '{{ _("text without line breaks or tabs") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#integer':
                case 'http://www.w3.org/2001/XMLSchema#int':
                    isValidDatatype = /^-?\d+$/.test(value);
                    expectedFormat = '{{ _("whole number") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#positiveInteger':
                    isValidDatatype = /^\d+$/.test(value) && parseInt(value) > 0;
                    expectedFormat = '{{ _("positive whole number") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#negativeInteger':
                    isValidDatatype = /^-\d+$/.test(value) && parseInt(value) < 0;
                    expectedFormat = '{{ _("negative whole number") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#nonNegativeInteger':
                    isValidDatatype = /^\d+$/.test(value) && parseInt(value) >= 0;
                    expectedFormat = '{{ _("non-negative whole number") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#nonPositiveInteger':
                    isValidDatatype = /^-?\d+$/.test(value) && parseInt(value) <= 0;
                    expectedFormat = '{{ _("non-positive whole number") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#byte':
                    isValidDatatype = /^-?\d+$/.test(value) && -128 <= parseInt(value) && parseInt(value) <= 127;
                    expectedFormat = '{{ _("whole number between -128 and 127") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#short':
                    isValidDatatype = /^-?\d+$/.test(value) && -32768 <= parseInt(value) && parseInt(value) <= 32767;
                    expectedFormat = '{{ _("whole number between -32768 and 32767") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#long':
                    isValidDatatype = /^-?\d+$/.test(value) && -2147483648 <= parseInt(value) && parseInt(value) <= 2147483647;
                    expectedFormat = '{{ _("whole number between -2147483648 and 2147483647") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#unsignedByte':
                    isValidDatatype = /^\d+$/.test(value) && 0 <= parseInt(value) && parseInt(value) <= 255;
                    expectedFormat = '{{ _("whole number between 0 and 255") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#unsignedShort':
                    isValidDatatype = /^\d+$/.test(value) && 0 <= parseInt(value) && parseInt(value) <= 65535;
                    expectedFormat = '{{ _("whole number between 0 and 65535") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#unsignedLong':
                case 'http://www.w3.org/2001/XMLSchema#unsignedInt':
                    isValidDatatype = /^\d+$/.test(value) && 0 <= parseInt(value) && parseInt(value) <= 4294967295;
                    expectedFormat = '{{ _("whole number between 0 and 4294967295") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#decimal':
                case 'http://www.w3.org/2001/XMLSchema#float':
                case 'http://www.w3.org/2001/XMLSchema#double':
                    isValidDatatype = /^-?\d*\.?\d+$/.test(value);
                    expectedFormat = '{{ _("number (can include decimal point)") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#duration':
                    isValidDatatype = /^P(?=\d|T\d)(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$/.test(value);
                    expectedFormat = '{{ _("duration (e.g. P1Y2M3DT4H5M6S)") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#dayTimeDuration':
                    isValidDatatype = /^P(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?$/.test(value);
                    expectedFormat = '{{ _("day and time duration (e.g. P1DT2H3M4S)") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#yearMonthDuration':
                    isValidDatatype = /^P(?:\d+Y)?(?:\d+M)?$/.test(value);
                    expectedFormat = '{{ _("year and month duration (e.g. P1Y2M)") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#gYearMonth':
                    isValidDatatype = /^(\d{4})-(\d{2})$/.test(value) && new Date(value + '-01').getMonth() === parseInt(value.split('-')[1]) - 1;
                    expectedFormat = '{{ _("year and month in format YYYY-MM") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#gYear':
                    isValidDatatype = /^\d{4}$/.test(value);
                    expectedFormat = '{{ _("year in format YYYY") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#dateTime':
                    isValidDatatype = /^-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$/.test(value);
                    expectedFormat = '{{ _("date and time (e.g. 2023-06-15T14:30:00+02:00)") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#dateTimeStamp':
                    isValidDatatype = /^-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$/.test(value);
                    expectedFormat = '{{ _("date and time with timezone (e.g. 2023-06-15T14:30:00+02:00)") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#date':
                    isValidDatatype = /^\d{4}-\d{2}-\d{2}$/.test(value) && !isNaN(new Date(value).getTime());
                    expectedFormat = '{{ _("date in format YYYY-MM-DD") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#time':
                    isValidDatatype = /^([01]\d|2[0-3]):?([0-5]\d):?([0-5]\d)$/.test(value);
                    expectedFormat = '{{ _("time in format HH:MM:SS") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#gMonth':
                    isValidDatatype = /^--(0[1-9]|1[0-2])$/.test(value);
                    expectedFormat = '{{ _("month in format --MM") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#gDay':
                    isValidDatatype = /^---(0[1-9]|[12]\d|3[01])$/.test(value);
                    expectedFormat = '{{ _("day in format ---DD") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#gMonthDay':
                    isValidDatatype = /^--(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/.test(value);
                    expectedFormat = '{{ _("month and day in format --MM-DD") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#boolean':
                    isValidDatatype = /^(true|false|1|0)$/i.test(value);
                    expectedFormat = '{{ _("true or false") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#hexBinary':
                    isValidDatatype = /^[0-9A-Fa-f]*$/.test(value);
                    expectedFormat = '{{ _("hexadecimal digits") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#base64Binary':
                    isValidDatatype = /^[A-Za-z0-9+/]*={0,2}$/.test(value);
                    expectedFormat = '{{ _("base64 encoded data") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#anyURI':
                    isValidDatatype = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/.test(value);
                    expectedFormat = '{{ _("valid URL") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#QName':
                case 'http://www.w3.org/2001/XMLSchema#NOTATION':
                    isValidDatatype = /^(?:[a-zA-Z_][\w.-]*:)?[a-zA-Z_][\w.-]*$/.test(value);
                    expectedFormat = '{{ _("qualified name") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#ENTITY':
                case 'http://www.w3.org/2001/XMLSchema#ID':
                case 'http://www.w3.org/2001/XMLSchema#IDREF':
                case 'http://www.w3.org/2001/XMLSchema#NCName':
                    isValidDatatype = /^[a-zA-Z_][\w.-]*$/.test(value);
                    expectedFormat = '{{ _("valid XML name") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#ENTITIES':
                case 'http://www.w3.org/2001/XMLSchema#IDREFS':
                    isValidDatatype = value.split(/\s+/).every(token => /^[a-zA-Z_][\w.-]*$/.test(token));
                    expectedFormat = '{{ _("list of valid XML names") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#NMTOKEN':
                    isValidDatatype = /^[\w.-]+$/.test(value);
                    expectedFormat = '{{ _("valid XML token") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#NMTOKENS':
                    isValidDatatype = value.split(/\s+/).every(token => /^[\w.-]+$/.test(token));
                    expectedFormat = '{{ _("list of valid XML tokens") }}';
                    break;
                case 'http://www.w3.org/2001/XMLSchema#Name':
                    isValidDatatype = /^[a-zA-Z_:][\w.-]*$/.test(value);
                    expectedFormat = '{{ _("valid XML Name") }}';
                    break;
            }
            if (isValidDatatype) return false; // Esci dal ciclo se trova un datatype valido
        });

        if (!isValidDatatype) {
            let fieldName = input.closest('.form-floating').find('label').text() || 
                            input.attr('placeholder') || 
                            input.attr('name') || 
                            '{{ _("This field") }}';
            errors.push({
                field: input,
                message: `${fieldName}: {{ _("Invalid input. Expected") }} ${expectedFormat}.`
            });
        }
    });
}

// Funzione per validare le condizioni
function validateConditions(errors) {
    $('input[data-conditions]:visible').each(function() {
        let input = $(this);
        let conditions = input.data('conditions');
        let value = input.val();

        conditions.forEach(function(conditionObj) {
            var condition = conditionObj.condition;
            var pattern = new RegExp(conditionObj.pattern);
            var message = conditionObj.message;

            var currentList = input.closest('[data-repeater-list]');
            var dependentField = currentList.siblings().find('[data-repeater-item]').not('.repeater-template').find('[data-predicate-uri="' + condition.path + '"]');

            var dependentValue;
            if (dependentField.is('select')) {
                dependentValue = dependentField.val();
            } else if (dependentField.is('input')) {
                dependentValue = dependentField.val();
            } else {
                var inputOrSelect = dependentField.find('input, select').closest();
                dependentValue = inputOrSelect.val();
            }

            // Controlla se il campo dipendente è disponibile e visibile
            if (dependentValue === condition.value) {
                // Applicare la validazione
                if (!pattern.test(value)) {
                    errors.push({
                        field: input,
                        message: message
                    });
                }
            }
        });
    });
}

$(document).ready(function() {
    // On change of date type selection
    $(document).on('change', '.date-type-selector', function() {
        showAppropriateDateInput($(this));
    });
});