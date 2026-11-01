// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

final List<String> externalNavigations = [];

void navigateExternally(String path) {
  externalNavigations.add(path);
}

bool navigateBack() => false;
