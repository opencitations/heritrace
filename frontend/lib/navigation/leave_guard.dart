// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Lets the page on screen confirm before the router leaves it.
class LeaveGuard {
  Future<bool> Function()? _confirm;

  void register(Future<bool> Function() confirm) => _confirm = confirm;

  void unregister(Future<bool> Function() confirm) {
    if (_confirm == confirm) {
      _confirm = null;
    }
  }

  Future<bool> canLeave() async {
    final confirm = _confirm;
    return confirm == null || await confirm();
  }
}

final leaveGuardProvider = Provider<LeaveGuard>((ref) => LeaveGuard());
