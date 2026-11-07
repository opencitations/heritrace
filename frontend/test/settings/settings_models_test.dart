// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/settings/settings_models.dart';

import 'fixtures.dart';

void main() {
  test('the settings survive a JSON round trip', () {
    final json = settingsJson();

    expect(SystemSettings.fromJson(json).toJson(), json);
  });
}
