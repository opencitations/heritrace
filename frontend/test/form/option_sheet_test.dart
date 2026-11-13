// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/design/controls.dart';
import 'package:heritrace/form/widgets/option_sheet.dart';
import 'package:heritrace/i18n/translations.g.dart';

void main() {
  Future<void> pumpButton(
    WidgetTester tester,
    int count, {
    ValueChanged<String?>? onChanged,
    String? description,
  }) async {
    LocaleSettings.setLocaleSync(AppLocale.en);
    await tester.pumpWidget(
      TranslationProvider(
        child: CupertinoApp(
          home: CupertinoPageScaffold(
            child: Center(
              child: OptionsButton<String?>(
                title: 'Datatype',
                value: null,
                options: [
                  const AppMenuOption(null, 'Select an option'),
                  for (var i = 1; i < count; i++)
                    AppMenuOption(
                      'option$i',
                      'Option $i',
                      description: i == 1 ? description : null,
                    ),
                ],
                onChanged: onChanged ?? (_) {},
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Select an option'));
    await tester.pumpAndSettle();
  }

  testWidgets('a short list opens a menu', (tester) async {
    await pumpButton(tester, 10);

    expect(find.byType(CupertinoMenuItem), findsNWidgets(10));
    expect(find.byType(CupertinoSearchTextField), findsNothing);
  });

  testWidgets('an option shows its explanation under its name', (tester) async {
    await pumpButton(tester, 3, description: 'What option 1 does');

    expect(find.text('What option 1 does'), findsOneWidget);
  });

  testWidgets('a long list opens a sheet that finds options by label', (
    tester,
  ) async {
    String? chosen;
    await pumpButton(tester, 11, onChanged: (value) => chosen = value);

    expect(find.text('Datatype'), findsOneWidget);
    await tester.enterText(find.byType(CupertinoSearchTextField), 'option 1');
    await tester.pump();
    expect(find.text('Option 1'), findsOneWidget);
    expect(find.text('Option 10'), findsOneWidget);
    expect(find.text('Option 2'), findsNothing);

    await tester.tap(find.text('Option 10'));
    await tester.pumpAndSettle();
    expect(chosen, 'option10');
  });
}
