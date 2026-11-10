// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:heritrace/settings/settings_models.dart';

Json settingsJson() => {
  'appTitle': 'Paratext',
  'appSubtitle': 'Bibliographic data',
  'countLimit': 10000,
  'catalogueDefaultPerPage': 50,
  'datasetGenerationTime': '2024-12-25T00:00:00+00:00',
  'primarySource': 'https://example.org/source',
  'orcidSafelist': ['0000-0002-1825-0097'],
  'orphanHandling': 'ASK',
  'compositeHandling': 'KEEP',
};

Json storedJson() => {
  'settings': settingsJson(),
  'options': {
    'strategies': ['ASK', 'DELETE', 'KEEP'],
    'defaultCountLimit': 10000,
  },
};
