// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/design/controls.dart';

import '../helpers.dart';

void main() {
  testWidgets(
    'a multiline field starts at three lines and grows with its text',
    (tester) async {
      Future<double> height(String text, {required bool multiline}) async {
        await pumpApp(
          tester,
          child: CupertinoApp(
            home: CupertinoPageScaffold(
              child: AppTextField(
                key: UniqueKey(),
                controller: TextEditingController(text: text),
                multiline: multiline,
              ),
            ),
          ),
        );
        return tester.getSize(find.byType(CupertinoTextField)).height;
      }

      final oneLine = await height('', multiline: false);
      final empty = await height('', multiline: true);
      final tenLines = await height(
        List.filled(10, 'line').join('\n'),
        multiline: true,
      );
      final lineHeight = (empty - oneLine) / 2;

      expect(tenLines - empty, 7 * lineHeight);
    },
  );
}
