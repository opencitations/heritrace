// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/app.dart';
import 'package:heritrace/design/app_theme.dart';
import 'package:heritrace/history/history_models.dart';
import 'package:heritrace/history/history_repository.dart';
import 'package:heritrace/navigation/app_paths.dart';
import 'package:heritrace/navigation/app_router.dart';

import 'helpers.dart';

const _entity = 'urn:entity:1';

Map<String, dynamic> _snapshot(int index, String start, String? end) => {
  'index': index,
  'timestamp': start,
  'end_timestamp': end,
  'responsible_agent': {
    'kind': 'agent',
    'url': null,
    'label': 'Editor',
    'orcid_id': null,
  },
  'primary_source': {
    'kind': 'none',
    'url': null,
    'label': 'None',
    'extra': null,
    'entity_uri': null,
    'timestamp': null,
  },
  'description': 'Snapshot $index',
  'modifications': null,
  'can_restore': false,
};

class _FakeHistoryRepository extends HistoryRepository {
  _FakeHistoryRepository() : super(Dio());

  @override
  Future<EntityHistory> history(String uri) async => EntityHistory.fromJson({
    'entity_uri': _entity,
    'entity_label': 'Entity',
    'snapshots': [
      _snapshot(1, '2026-01-01T00:00:00+00:00', '2026-02-01T00:00:00+00:00'),
      _snapshot(2, '2026-02-01T00:00:00+00:00', null),
    ],
  });
}

void main() {
  for (final textScale in [1.0, 1.3]) {
    testWidgets('only the current version has a filled node, centred on its '
        'title line at text scale $textScale', (tester) async {
      tester.platformDispatcher.textScaleFactorTestValue = textScale;
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
      await pumpApp(
        tester,
        child: const App(),
        overrides: [
          historyRepositoryProvider.overrideWithValue(_FakeHistoryRepository()),
        ],
      );
      ProviderScope.containerOf(tester.element(find.byType(App)))
          .read(routerProvider)
          .go(entityHistoryPath(_entity));
      await tester.pumpAndSettle();

      final nodes = find.byWidgetPredicate(
        (widget) =>
            widget is Container &&
            widget.constraints?.maxWidth == 12 &&
            (widget.decoration as BoxDecoration?)?.shape == BoxShape.circle,
      );
      expect(nodes, findsNWidgets(2));
      final fills = [
        for (final node in tester.widgetList<Container>(nodes))
          (node.decoration! as BoxDecoration).color,
      ];
      expect(fills.first, AppColors.primary);
      expect(fills.last, isNot(AppColors.primary));

      for (final (index, node) in [(2, nodes.first), (1, nodes.last)]) {
        final title = find.text('Version $index');
        expect(
          tester.getCenter(node).dy,
          closeTo(tester.getCenter(title).dy, 0.5),
        );
      }
    });
  }
}
