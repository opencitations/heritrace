// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/entity/edit_session.dart';
import 'package:heritrace/entity/entity_models.dart';
import 'package:heritrace/form/field_def.dart';
import 'package:heritrace/form/form_model.dart';

const hidden = 'http://datashapes.org/dash#hidden';
const shape = 'https://example.org/shape';

final field = FieldDef.fromJson({
  'uri': hidden,
  'inputType': 'checkbox',
  'max': 1,
});

EditableGroup editableGroup(List<String> values, {bool addable = true}) =>
    EditableGroup(
      group: PropertyGroup(
        displayName: 'Hidden',
        property: hidden,
        objectShape: null,
        isDraggable: false,
        orderedBy: null,
        field: field,
        triples: [
          for (final value in values)
            EntityTriple(
              subject: shape,
              predicate: hidden,
              value: value,
              object: value,
              language: null,
              externalEntity: null,
              isMandatory: false,
              label: null,
              details: null,
            ),
        ],
      ),
      formGroup: addable ? FieldGroup(def: field, depth: 0) : null,
    );

void main() {
  test('switching on a missing value adds true, switching off removes it', () {
    final group = editableGroup([]);
    expect(group.isSwitchedOn, isFalse);
    group.switchTo(true);
    expect(group.isSwitchedOn, isTrue);
    expect(group.formGroup!.items.single.textValue, 'true');
    group.switchTo(false);
    expect(group.formGroup!.items, isEmpty);
  });

  test(
    'switching off a stored true deletes it, switching back restores it',
    () {
      final group = editableGroup(['true']);
      final value = group.existing.single;
      group.switchTo(false);
      expect(group.isSwitchedOn, isFalse);
      expect(value.markedForDeletion, isTrue);
      group.switchTo(true);
      expect(value.markedForDeletion, isFalse);
      expect(value.isModified, isFalse);
    },
  );

  test('switching on a stored false updates it to true', () {
    final group = editableGroup(['false']);
    group.switchTo(true);
    expect(group.existing.single.newValue, 'true');
    group.switchTo(false);
    expect(group.existing.single.isModified, isFalse);
    expect(group.existing.single.markedForDeletion, isFalse);
  });

  test('a missing value that cannot be added reads as off', () {
    final group = editableGroup([], addable: false);
    expect(group.isSwitchedOn, isFalse);
    expect(group.canSwitch, isFalse);
  });
}
