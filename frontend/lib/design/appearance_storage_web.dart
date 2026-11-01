// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:web/web.dart' as web;

const _key = 'appearance';

String? readAppearance() => web.window.localStorage.getItem(_key);

void writeAppearance(String name) =>
    web.window.localStorage.setItem(_key, name);
