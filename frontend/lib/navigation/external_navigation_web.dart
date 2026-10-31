// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:web/web.dart' as web;

void navigateExternally(String path) {
  web.window.location.assign(path);
}
