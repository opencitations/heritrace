// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

final _orcidShape = RegExp(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$');

/// The bare iD of an ORCID iD or of its https://orcid.org/ address.
String orcidIdOf(String value) {
  final uri = Uri.tryParse(value);
  return uri != null && uri.host == 'orcid.org'
      ? uri.path.replaceAll('/', '')
      : value;
}

/// Checks the shape and the ISO 7064 MOD 11-2 check digit, as described at
/// https://support.orcid.org/hc/en-us/articles/360006897674
bool isValidOrcidId(String id) {
  if (!_orcidShape.hasMatch(id)) {
    return false;
  }
  final digits = id.replaceAll('-', '');
  var total = 0;
  for (final digit in digits.substring(0, digits.length - 1).split('')) {
    total = (total + int.parse(digit)) * 2;
  }
  final check = (12 - total % 11) % 11;
  return digits[digits.length - 1] == (check == 10 ? 'X' : '$check');
}

sealed class OrcidLookup {
  const OrcidLookup();
}

class OrcidFound extends OrcidLookup {
  const OrcidFound(this.name);

  /// Null when the owner keeps the name private.
  final String? name;
}

class OrcidMissing extends OrcidLookup {
  const OrcidMissing();
}

class OrcidUnreachable extends OrcidLookup {
  const OrcidUnreachable();
}
