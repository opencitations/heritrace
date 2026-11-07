// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter/gestures.dart';

import 'app_theme.dart';

// Dates and times get separate wheels because the single date-and-time
// wheel has no year column: a date far from today would take thousands of
// turns.
Future<DateTime?> showDateTimeSheet(
  BuildContext context, {
  required DateTime initial,
  required String doneLabel,
  bool withTime = false,
}) {
  var selected = initial;
  return showCupertinoModalPopup<DateTime>(
    context: context,
    builder: (context) => Container(
      height: withTime ? 480 : 300,
      color: AppColors.of(context).surface,
      child: SafeArea(
        top: false,
        child: SelectionContainer.disabled(
          // The wheels hold no text to select, so a mouse can drag them too.
          child: ScrollConfiguration(
            behavior: ScrollConfiguration.of(context).copyWith(
              dragDevices: {
                ...ScrollConfiguration.of(context).dragDevices,
                PointerDeviceKind.mouse,
              },
            ),
            child: Column(
              children: [
                Align(
                  alignment: Alignment.centerRight,
                  child: CupertinoButton(
                    onPressed: () => Navigator.of(context).pop(selected),
                    child: Text(doneLabel),
                  ),
                ),
                Expanded(
                  child: CupertinoDatePicker(
                    mode: CupertinoDatePickerMode.date,
                    initialDateTime: initial,
                    minimumYear: 1000,
                    maximumYear: 9999,
                    onDateTimeChanged: (value) => selected = DateTime(
                      value.year,
                      value.month,
                      value.day,
                      selected.hour,
                      selected.minute,
                    ),
                  ),
                ),
                if (withTime)
                  Expanded(
                    child: CupertinoDatePicker(
                      mode: CupertinoDatePickerMode.time,
                      initialDateTime: initial,
                      onDateTimeChanged: (value) => selected = DateTime(
                        selected.year,
                        selected.month,
                        selected.day,
                        value.hour,
                        value.minute,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
