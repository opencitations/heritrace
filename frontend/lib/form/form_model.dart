// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/widgets.dart';

import 'field_def.dart';

enum DateType { date, month, year }

List<DateType> dateTypesFor(List<String> datatypes) => [
  if (datatypes.contains(xsdDate)) DateType.date,
  if (datatypes.contains(xsdGYearMonth)) DateType.month,
  if (datatypes.contains(xsdGYear)) DateType.year,
];

int _tempIdCounter = 0;

String nextTempId() => 'temp-${++_tempIdCounter}';

/// A node of the editable entity tree. Groups are the SHACL properties of the
/// entity; each group holds the values the user has entered.
class EntityNode extends ChangeNotifier {
  EntityNode({
    required this.entityType,
    required this.entityShape,
    required List<FieldDef> fields,
    required this.depth,
    this.parentPredicate,
    this.parentEntityType,
    bool fillMinimum = true,
  }) : groups = [for (final def in fields) FieldGroup(def: def, depth: depth)] {
    for (final group in groups) {
      group.owner = this;
      group.addListener(notifyListeners);
      if (fillMinimum) {
        group.fillMinimum();
      }
    }
  }

  final String entityType;
  final String? entityShape;
  final int depth;
  final String? parentPredicate;
  final String? parentEntityType;
  final List<FieldGroup> groups;
  NestedItem? parentItem;

  @override
  void dispose() {
    for (final group in groups) {
      group.dispose();
    }
    super.dispose();
  }
}

class FieldGroup extends ChangeNotifier {
  FieldGroup({required this.def, required this.depth});

  final FieldDef def;
  final int depth;
  final List<FormItem> items = [];
  late EntityNode owner;

  bool get canAdd => def.max == null || items.length < def.max!;

  bool canDelete(FormItem item) {
    if (def.hasValue != null) {
      return false;
    }
    if (def.max == 1 && def.min == 0) {
      return true;
    }
    return def.min == 0 || items.indexOf(item) >= def.min;
  }

  void fillMinimum() {
    while (items.length < def.min) {
      addItem(notify: false);
    }
  }

  FormItem addItem({bool notify = true}) {
    final item = createItem(def, depth, this);
    items.add(item);
    item.addListener(notifyListeners);
    if (notify) {
      notifyListeners();
    }
    return item;
  }

  void removeItem(FormItem item) {
    items.remove(item);
    item.dispose();
    notifyListeners();
  }

  void move(int oldIndex, int newIndex) {
    final item = items.removeAt(oldIndex);
    items.insert(newIndex, item);
    notifyListeners();
  }

  @override
  void dispose() {
    for (final item in items) {
      item.dispose();
    }
    super.dispose();
  }
}

FormItem createItem(FieldDef def, int depth, FieldGroup group) {
  final item = switch (def.kind) {
    FieldKind.or => OrItem(def: def, depth: depth),
    FieldKind.nested => NestedItem(def: def, depth: depth),
    FieldKind.mandatory => MandatoryItem(def: def, depth: depth),
    FieldKind.select => SelectItem(def: def, depth: depth),
    FieldKind.date => DateItem(def: def, depth: depth),
    FieldKind.literal => LiteralItem(def: def, depth: depth),
  };
  item.group = group;
  if (def.orderedBy != null) {
    item.tempId = nextTempId();
  }
  if (item is NestedItem) {
    item.child = item.buildChild();
  }
  return item;
}

sealed class FormItem extends ChangeNotifier {
  FormItem({required this.def, required this.depth});

  final FieldDef def;
  final int depth;
  late FieldGroup group;
  String? tempId;
  bool touched = false;
  final FocusNode focusNode = FocusNode();

  /// The textual value for literal-like items; null for nested ones.
  String? get textValue => null;

  bool get isEmpty => (textValue ?? '').trim().isEmpty;

  void markTouched() {
    if (!touched) {
      touched = true;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    focusNode.dispose();
    super.dispose();
  }
}

class LiteralItem extends FormItem {
  LiteralItem({required super.def, required super.depth});

  String value = '';

  @override
  String get textValue => value;

  void setValue(String next) {
    value = next;
    touched = true;
    notifyListeners();
  }
}

class SelectItem extends FormItem {
  SelectItem({required super.def, required super.depth});

  String? value;

  @override
  String get textValue => value ?? '';

  void setValue(String? next) {
    value = next;
    touched = true;
    notifyListeners();
  }
}

class MandatoryItem extends FormItem {
  MandatoryItem({required super.def, required super.depth});

  @override
  String get textValue => def.hasValue!;
}

class DateItem extends FormItem {
  DateItem({required super.def, required super.depth})
    : dateType = dateTypesFor(def.datatypes).first;

  DateType dateType;
  String value = '';

  @override
  String get textValue => value;

  String get datatype => switch (dateType) {
    DateType.date => xsdDate,
    DateType.month => xsdGYearMonth,
    DateType.year => xsdGYear,
  };

  void setValue(String next) {
    value = next;
    touched = true;
    notifyListeners();
  }

  void setDateType(DateType next) {
    if (value.isNotEmpty) {
      value = convertDate(value, next);
    }
    dateType = next;
    touched = true;
    notifyListeners();
  }
}

String convertDate(String original, DateType type) {
  var normalized = original;
  if (RegExp(r'^\d{4}$').hasMatch(normalized)) {
    normalized += '-01-01';
  } else if (RegExp(r'^\d{4}-\d{2}$').hasMatch(normalized)) {
    normalized += '-01';
  }
  final parsed = DateTime.tryParse(normalized);
  if (parsed == null) {
    return original;
  }
  final iso = parsed.toIso8601String();
  return switch (type) {
    DateType.date => iso.substring(0, 10),
    DateType.month => iso.substring(0, 7),
    DateType.year => iso.substring(0, 4),
  };
}

/// A nested entity, filled in through the nested dialog. Selecting an existing
/// entity from the search results replaces the child form with a reference.
class NestedItem extends FormItem {
  NestedItem({required super.def, required super.depth});

  late EntityNode child;
  String? existingUri;
  String? existingLabel;
  String? draftLabel;
  bool draftLabelFailed = false;
  bool discardIfUntouched = false;

  bool get isExisting => existingUri != null;

  EntityNode buildChild() {
    final node = EntityNode(
      entityType: def.childEntityType,
      entityShape: def.childEntityShape,
      fields: def.childFields,
      depth: depth + 1,
      parentPredicate: def.uri,
      parentEntityType: group.owner.entityType,
    );
    node.parentItem = this;
    node.addListener(_onChildChanged);
    return node;
  }

  void _onChildChanged() {
    touched = true;
    notifyListeners();
  }

  void setDraftLabel(String? label, {required bool failed}) {
    draftLabel = label;
    draftLabelFailed = failed;
    notifyListeners();
  }

  void selectExisting(String uri, String label) {
    existingUri = uri;
    existingLabel = label;
    touched = true;
    notifyListeners();
  }

  void clearExisting() {
    existingUri = null;
    existingLabel = null;
    child.dispose();
    child = buildChild();
    notifyListeners();
  }

  @override
  void dispose() {
    child.dispose();
    super.dispose();
  }
}

/// A `sh:or` field: the user picks one of the alternative shapes, then fills
/// the group built for that shape.
class OrItem extends FormItem {
  OrItem({required super.def, required super.depth});

  FieldDef? selected;
  FieldGroup? selectedGroup;

  void select(FieldDef? option) {
    selectedGroup?.dispose();
    selected = option;
    if (option == null) {
      selectedGroup = null;
    } else {
      final group = FieldGroup(def: option, depth: depth)
        ..owner = this.group.owner;
      group
        ..addListener(notifyListeners)
        ..addItem(notify: false);
      selectedGroup = group;
    }
    touched = true;
    notifyListeners();
  }

  @override
  void dispose() {
    selectedGroup?.dispose();
    super.dispose();
  }
}

/// A free-form property used when no SHACL shape applies.
class CustomProperty extends ChangeNotifier {
  String predicate = '';
  String value = '';
  String type = 'literal';
  String datatype = xsdString;
  List<String>? validDatatypes;

  bool get isComplete => predicate.trim().isNotEmpty && value.trim().isNotEmpty;

  void update({
    String? predicate,
    String? value,
    String? type,
    String? datatype,
  }) {
    this.predicate = predicate ?? this.predicate;
    this.value = value ?? this.value;
    this.type = type ?? this.type;
    this.datatype = datatype ?? this.datatype;
    notifyListeners();
  }

  /// Restricts the datatype choice to [valid]; `null` lifts the restriction.
  void setValidDatatypes(List<String>? valid) {
    validDatatypes = valid;
    if (valid != null && valid.isNotEmpty && !valid.contains(datatype)) {
      datatype = valid.first;
    }
    notifyListeners();
  }
}
