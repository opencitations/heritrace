// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';
import 'package:heritrace/app.dart';
import 'package:heritrace/navigation/external_navigation.dart';

import 'helpers.dart';

void main() {
  testWidgets('shows the landing page with the configured title', (
    tester,
  ) async {
    await pumpApp(tester, child: const App());
    await tester.pumpAndSettle();

    expect(find.text('HERITRACE Test'), findsWidgets);
    expect(find.text('Test subtitle'), findsOneWidget);
    expect(find.text('Go to the catalogue'), findsOneWidget);
  });

  testWidgets('anonymous users see the login action', (tester) async {
    externalNavigations.clear();
    await pumpApp(tester, child: const App(), session: anonymousSession);
    await tester.pumpAndSettle();

    expect(find.text('Login'), findsOneWidget);
    expect(find.text('Logout'), findsNothing);
    expect(externalNavigations, isEmpty);
  });

  testWidgets('the account menu switches the interface language', (
    tester,
  ) async {
    await pumpApp(tester, child: const App());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Test User'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Italiano'));
    await tester.pumpAndSettle();

    expect(find.text('Vai al catalogo'), findsOneWidget);
    expect(Intl.defaultLocale, 'it');
  });
}
