// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

final _whitespace = RegExp(r'\s');

/// The same test the server applies: a scheme and no spaces.
bool isIri(String value) =>
    Uri.tryParse(value)?.hasScheme == true && !value.contains(_whitespace);
