// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:js_interop';

import 'package:web/web.dart' as web;

void navigateExternally(String path) {
  web.window.location.assign(path);
}

/// The Flutter engine numbers the browser history entries it creates from 0,
/// the page the app was opened on, so a positive number means an earlier page
/// of the app is one step back.
bool navigateBack() {
  final state = web.window.history.state.dartify();
  final serialCount = state is Map ? state['serialCount'] : null;
  if (serialCount is! num || serialCount == 0) {
    return false;
  }
  web.window.history.back();
  return true;
}
