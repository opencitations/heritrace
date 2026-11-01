// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/gestures.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/app.dart';
import 'package:heritrace/navigation/app_router.dart';

import 'helpers.dart';

void main() {
  late String? clipboard;

  setUp(() {
    clipboard = null;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, (call) async {
          if (call.method == 'Clipboard.setData') {
            clipboard = (call.arguments as Map)['text'] as String;
          }
          return null;
        });
  });

  Future<void> drag(WidgetTester tester, Finder from, Finder to) async {
    final gesture = await tester.startGesture(
      tester.getRect(from).centerLeft + const Offset(-2, 0),
      kind: PointerDeviceKind.mouse,
    );
    await tester.pump();
    await gesture.moveTo(tester.getRect(to).centerRight + const Offset(2, 0));
    await tester.pump();
    await gesture.up();
    await tester.pump();
  }

  Future<void> copy(WidgetTester tester) async {
    await tester.sendKeyDownEvent(LogicalKeyboardKey.control);
    await tester.sendKeyEvent(LogicalKeyboardKey.keyC);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.control);
    await tester.pump();
  }

  testWidgets('page text can be selected and copied', (tester) async {
    await pumpApp(tester, child: const App());
    await tester.pumpAndSettle();

    final subtitle = find.text('Test subtitle');
    await drag(tester, subtitle, subtitle);
    await copy(tester);

    expect(clipboard, 'Test subtitle');
  });

  testWidgets('button labels are left out of the selection', (tester) async {
    await pumpApp(tester, child: const App());
    await tester.pumpAndSettle();

    await drag(
      tester,
      find.text('Test subtitle'),
      find.text('Go to the catalogue'),
    );
    await copy(tester);

    expect(clipboard, startsWith('Test subtitle'));
    expect(clipboard, isNot(contains('Go to the catalogue')));
  });

  testWidgets('moving to another page clears the selection', (tester) async {
    await pumpApp(tester, child: const App());
    await tester.pumpAndSettle();

    final subtitle = find.text('Test subtitle');
    await drag(tester, subtitle, subtitle);
    ProviderScope.containerOf(tester.element(find.byType(App)))
        .read(routerProvider)
        .go('/missing');
    await tester.pumpAndSettle();
    await copy(tester);

    expect(clipboard, isNull);
  });
}
