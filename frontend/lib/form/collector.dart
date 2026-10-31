// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'field_def.dart';
import 'form_model.dart';

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
    if (item is OrItem && item.selectedGroup != null) {
      _collectGroup(item.selectedGroup!, data);
    }
  }
}

Object? collectItem(FormItem item) => switch (item) {
  LiteralItem() ||
  SelectItem() ||
  DateItem() ||
  MandatoryItem() => item.isEmpty ? null : item.textValue,
  NestedItem() => collectNested(item),
  OrItem() => null,
};

Map<String, Object>? collectNested(NestedItem item) {
  final def = item.def;
  final relation = def.intermediateRelation;
  final properties = item.isExisting
      ? <String, List<Object>>{}
      : collectProperties(item.child);
  final orderedBy = def.orderedBy;

  if (relation != null) {
    final entity = <String, Object>{
      'entity_type': relation.intermediateClass,
      'entity_shape': ?def.nodeShape,
      'properties': <String, Object>{},
      'targetEntityType': relation.targetEntityType,
      'targetShape': ?relation.targetShape,
    };
    final entityProperties = entity['properties'] as Map<String, Object>;
    final connecting = relation.connectingProperty!;
    if (properties.isNotEmpty) {
      entityProperties[connecting] = {
        'entity_type': item.child.entityType,
        'entity_shape': ?(relation.targetShape ?? def.nodeShape),
        'properties': properties,
      };
    } else if (item.isExisting) {
      entityProperties[connecting] = [
        {'is_existing_entity': true, 'entity_uri': item.existingUri!},
      ];
    } else {
      return null;
    }
    entityProperties.addAll(def.additionalProperties);
    if (orderedBy != null) {
      entity['orderedBy'] = orderedBy;
    }
    if (item.tempId != null) {
      entity['tempId'] = item.tempId!;
    }
    return entity;
  }

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
