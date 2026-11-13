// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/form/field_def.dart';

void main() {
  test('a field without a name is named after its IRI, acronyms whole', () {
    const names = {
      'http://example.org/hasPublicationDate': 'Has publication date',
      'http://www.w3.org/2001/XMLSchema#anyURI': 'Any URI',
      'http://www.w3.org/2001/XMLSchema#NCName': 'NC name',
      'http://www.w3.org/2001/XMLSchema#ENTITIES': 'ENTITIES',
      'http://www.w3.org/2001/XMLSchema#base64Binary': 'Base64 binary',
      'http://example.org/cittàNatale': 'Città natale',
    };
    for (final MapEntry(key: uri, value: name) in names.entries) {
      expect(FieldDef.fromJson({'uri': uri}).displayName, name);
    }
  });
}
