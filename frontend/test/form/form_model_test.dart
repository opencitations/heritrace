// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/form/field_def.dart';
import 'package:heritrace/form/form_model.dart';

const _sh = 'http://www.w3.org/ns/shacl#';
const _datatype = '${_sh}datatype';
const _node = '${_sh}node';
const _class = '${_sh}class';
const _hasValue = '${_sh}hasValue';

Map<String, dynamic> _constraint(String uri, List<String> excludedWith) => {
  'uri': uri,
  'entityType': 'https://w3id.org/heritrace#ValueAlternative',
  'max': 1,
  'excludedWith': excludedWith,
};

FieldGroup _alternatives() {
  final field = EntityNode(
    entityType: '${_sh}PropertyShape',
    entityShape: null,
    fields: [
      FieldDef.fromJson({
        'uri': '${_sh}or',
        'nodeShape': 'https://w3id.org/heritrace/meta/ValueAlternativeShape',
        'nestedShape': [
          _constraint(_datatype, [_node, _class, _hasValue]),
          _constraint(_node, [_datatype, _hasValue]),
          _constraint(_class, [_datatype, _hasValue]),
          _constraint(_hasValue, [_datatype, _node, _class]),
        ],
      }),
    ],
    depth: 0,
  );
  addTearDown(field.dispose);
  return field.groups.single;
}

List<String> _shown(NestedItem item) => [
  for (final group in item.child.shownGroups(null)) group.def.uri,
];

void main() {
  test('a new resource of a list leaves out what its siblings exclude', () {
    final alternatives = _alternatives();
    final first = alternatives.addItem() as NestedItem;
    final second = alternatives.addItem() as NestedItem;
    final shownBefore = _shown(second);

    final datatype = first.child.groups.firstWhere(
      (group) => group.def.uri == _datatype,
    );
    (datatype.addItem() as LiteralItem).setValue(xsdDate);

    expect(
      [shownBefore, _shown(first), _shown(second)],
      [
        [_datatype, _node, _class, _hasValue],
        [_datatype],
        [_datatype],
      ],
    );
  });

  test('a new resource of a list follows the resources already saved', () {
    final alternatives = _alternatives()
      ..savedItemFields = () => [_node, _class];

    final item = alternatives.addItem() as NestedItem;

    expect(_shown(item), [_node, _class]);
  });
}
