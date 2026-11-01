// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:web/web.dart' as web;

String? readPreference(String key) => web.window.localStorage.getItem(key);

void writePreference(String key, String value) =>
    web.window.localStorage.setItem(key, value);
