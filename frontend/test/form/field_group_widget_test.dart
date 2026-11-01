// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/form/field_def.dart';
import 'package:heritrace/form/form_model.dart';
import 'package:heritrace/form/form_scope.dart';
import 'package:heritrace/design/controls.dart';
import 'package:heritrace/form/widgets/field_group_widget.dart';
import 'package:heritrace/form/widgets/item_widgets.dart';
import 'package:heritrace/i18n/translations.g.dart';

import 'fixtures.dart';

Future<void> pumpGroup(WidgetTester tester, FieldGroup group) async {
  LocaleSettings.setLocale(AppLocale.en);
  tester.view.physicalSize = const Size(1280, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    TranslationProvider(
      child: ProviderScope(
        child: CupertinoApp(
          home: CupertinoPageScaffold(
            child: FormScope(
              notifier: FormScopeController(rootLabel: 'Journal Article'),
              child: SingleChildScrollView(
                child: FieldGroupWidget(group: group),
              ),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pump();
}

void main() {
  late EntityNode root;

  setUp(() {
    root = EntityNode(
      entityType: article,
      entityShape: articleShape,
      fields: articleFields(),
      depth: 0,
    );
  });

  tearDown(() => root.dispose());

  FieldGroup group(String uri) =>
      root.groups.firstWhere((g) => g.def.uri == uri);

  testWidgets('a required single value has neither add nor delete actions', (
    tester,
  ) async {
    await pumpGroup(tester, group(title));

    expect(find.text('Title'), findsNWidgets(2));
    expect(find.text('Add Title'), findsNothing);
    expect(find.text('Delete'), findsNothing);
    expect(find.byType(CupertinoTextField), findsOneWidget);

    await tester.enterText(find.byType(CupertinoTextField), 'A new title');
    expect((group(title).items.single as LiteralItem).value, 'A new title');
  });

  testWidgets('an optional single value can be added once and removed', (
    tester,
  ) async {
    await pumpGroup(tester, group(pubDate));

    expect(find.text('Add Publication Date'), findsOneWidget);
    await tester.tap(find.text('Add Publication Date'));
    await tester.pump();

    expect(find.text('Add Publication Date'), findsNothing);
    expect(find.text('Delete'), findsOneWidget);
    expect(find.byType(DateTypeMenu), findsOneWidget);

    await tester.tap(find.text('Delete'));
    await tester.pump();

    expect(group(pubDate).items, isEmpty);
    expect(find.text('Add Publication Date'), findsOneWidget);
  });

  testWidgets('closing an untouched new nested entity discards it', (
    tester,
  ) async {
    await pumpGroup(tester, group(documentContext));

    await tester.tap(find.text('Add Author'));
    await tester.pumpAndSettle();
    expect(group(documentContext).items, hasLength(1));

    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(group(documentContext).items, isEmpty);
  });

  testWidgets('mandatory values show their label and an explanation', (
    tester,
  ) async {
    await pumpGroup(tester, group(rdfType));

    expect(find.text('Journal Article'), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is AppTooltip &&
            widget.message ==
                'This property has a mandatory value that cannot be modified',
      ),
      findsOneWidget,
    );
    expect(find.text('Delete'), findsNothing);
  });
}
