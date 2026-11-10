// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'field_def.dart';
import 'form_model.dart';
import 'validator.dart';

/// Builds the `properties` map accepted by the backend from the editable tree.
/// Empty values are skipped, so an untouched nested entity contributes nothing.
Map<String, List<Object>> collectProperties(EntityNode node) {
  final data = <String, List<Object>>{};
  for (final group in node.groups) {
    _collectGroup(group, data);
  }
  return data;
}

void _collectGroup(FieldGroup group, Map<String, List<Object>> data) {
  for (final item in group.items) {
    final value = collectItem(item);
    if (value != null) {
      data.putIfAbsent(group.def.uri, () => []).add(value);
    }
  }
}

Object? collectItem(FormItem item) => switch (item) {
  LiteralItem() ||
  SelectItem() ||
  DateItem() ||
  MandatoryItem() => item.isEmpty ? null : item.textValue,
  NestedItem() => collectNested(item),
  OrItem(:final selectedItem) =>
    selectedItem == null ? null : collectItem(selectedItem),
};

Map<String, Object>? collectNested(NestedItem item) {
  final def = item.def;
  if (def.detailsEditor && !hasAnyValue(item.child)) {
    return null;
  }
  final properties = item.isExisting
      ? <String, List<Object>>{}
      : collectProperties(item.child);
  final orderedBy = def.orderedBy;

  if (properties.isNotEmpty) {
    return {
      'entity_type': item.child.entityType,
      'entity_shape': ?def.nodeShape,
      'properties': properties,
      'orderedBy': ?orderedBy,
      'tempId': ?item.tempId,
    };
  }
  if (item.isExisting) {
    return {'is_existing_entity': true, 'entity_uri': item.existingUri!};
  }
  return null;
}

/// The entity sent to `/api/draft-labels` for a nested item: the same value
/// the collector produces, with the type and shape of the nested entity.
Map<String, Object>? draftEntity(NestedItem item) {
  final value = collectNested(item);
  if (value == null || value.containsKey('is_existing_entity')) {
    return null;
  }
  return value;
}

Map<String, List<Object>> collectCustomProperties(
  Iterable<CustomProperty> properties,
) {
  final data = <String, List<Object>>{};
  for (final property in properties) {
    if (!property.isComplete) {
      continue;
    }
    data.putIfAbsent(property.predicate.trim(), () => []).add({
      'is_custom_property': true,
      'value': property.value,
      'type': property.type,
      if (property.type == 'literal') 'datatype': property.datatype,
    });
  }
  return data;
}

const owlThing = 'http://www.w3.org/2002/07/owl#Thing';

/// The `structured_data` payload of entity creation without SHACL: the first
/// `rdf:type` custom property becomes the entity type.
Map<String, Object> customCreationPayload(Iterable<CustomProperty> properties) {
  final collected = collectCustomProperties(properties);
  final types = collected.remove(rdfType);
  final entityType = types == null
      ? owlThing
      : (types.first as Map<String, Object>)['value'] as String;
  return {'entity_type': entityType, 'properties': collected};
}
