// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:flutter/foundation.dart';

import '../form/collector.dart';
import '../form/field_def.dart';
import '../form/form_model.dart';
import '../form/validator.dart';
import '../form/widgets/custom_properties_form.dart';
import 'entity_models.dart';
import 'entity_repository.dart';

const lockRenewalInterval = Duration(seconds: 240);

class ExistingValue extends ChangeNotifier {
  ExistingValue({required this.triple, required this.group})
    : newValue = triple.value,
      dateType = _dateTypeFor(triple.value);

  final EntityTriple triple;
  final PropertyGroup group;
  String newValue;
  DateType dateType;
  bool markedForDeletion = false;

  bool get isModified => newValue != triple.value;

  bool get isEntityLink => triple.externalEntity != null;

  static DateType _dateTypeFor(String value) => switch (value.length) {
    7 => DateType.month,
    4 => DateType.year,
    _ => DateType.date,
  };

  void setValue(String value) {
    newValue = value;
    notifyListeners();
  }

  void setDateType(DateType type) {
    if (newValue.isNotEmpty) {
      newValue = convertDate(newValue, type);
    }
    dateType = type;
    notifyListeners();
  }

  void markForDeletion() {
    markedForDeletion = true;
    notifyListeners();
  }

  void undoDeletion() {
    markedForDeletion = false;
    notifyListeners();
  }

  void reset() {
    newValue = triple.value;
    dateType = _dateTypeFor(triple.value);
    markedForDeletion = false;
    notifyListeners();
  }
}

/// The values shown for one property group: the existing triples in their
/// current order plus the new items added in edit mode.
class EditableGroup extends ChangeNotifier {
  EditableGroup({required this.group, required this.formGroup}) {
    existing = [
      for (final triple in group.triples)
        ExistingValue(triple: triple, group: group),
    ];
    for (final value in existing) {
      value.addListener(notifyListeners);
    }
    formGroup?.addListener(notifyListeners);
  }

  final PropertyGroup group;
  final FieldGroup? formGroup;
  late final List<ExistingValue> existing;

  List<String> get originalOrder => [
    for (final triple in group.triples) triple.object,
  ];

  List<String> get currentOrder => [
    for (final value in existing)
      if (!value.markedForDeletion) value.triple.object,
    for (final item in formGroup?.items ?? const <FormItem>[])
      if (item.tempId != null) item.tempId!,
  ];

  bool get orderChanged =>
      group.orderedBy != null &&
      (existing.any((value) => value.markedForDeletion) ||
          (formGroup?.items.isNotEmpty ?? false) ||
          !listEquals(originalOrder, currentOrder));

  void move(int oldIndex, int newIndex) {
    final value = existing.removeAt(oldIndex);
    existing.insert(newIndex, value);
    notifyListeners();
  }

  void reset() {
    existing.sort(
      (a, b) => group.triples
          .indexOf(a.triple)
          .compareTo(group.triples.indexOf(b.triple)),
    );
    for (final value in existing) {
      value.reset();
    }
    final items = [...?formGroup?.items];
    for (final item in items) {
      formGroup!.removeItem(item);
    }
    notifyListeners();
  }

  @override
  void dispose() {
    for (final value in existing) {
      value.dispose();
    }
    super.dispose();
  }
}

enum EditStatus { viewing, starting, editing, saving }

class EditSession extends ChangeNotifier {
  EditSession({
    required this.view,
    required this.entityType,
    required this.repository,
    required this.validationMessages,
    required this.atLeastOnePropertyMessage,
  }) {
    final addable = <FieldDef>[];
    for (final group in view.groups) {
      final field = group.field;
      if (field != null && view.canBeAdded.contains(group.property)) {
        addable.add(field);
      }
    }
    root = EntityNode(
      entityType: entityType,
      entityShape: view.shape,
      fields: addable,
      depth: 0,
      fillMinimum: false,
    );
    root.addListener(notifyListeners);
    customProperties.addListener(notifyListeners);
    final formGroups = {for (final group in root.groups) group.def: group};
    groups = [
      for (final group in view.groups)
        EditableGroup(group: group, formGroup: formGroups[group.field]),
    ];
    for (final group in groups) {
      group.addListener(notifyListeners);
    }
  }

  final EntityView view;
  final String entityType;
  final EntityRepository repository;
  final ValidationMessages validationMessages;
  final String atLeastOnePropertyMessage;
  late final EntityNode root;
  late final List<EditableGroup> groups;
  final CustomPropertiesController customProperties =
      CustomPropertiesController();
  EditStatus status = EditStatus.viewing;
  bool saved = false;
  Timer? _renewTimer;
  bool _disposed = false;
  void Function()? onLockLost;

  bool get editing =>
      status == EditStatus.editing || status == EditStatus.saving;

  bool get showsCustomProperties => !view.shacl || !view.hasFormFields;

  bool get hasChanges =>
      groups.any(
        (group) =>
            group.existing.any((v) => v.isModified || v.markedForDeletion) ||
            group.orderChanged,
      ) ||
      collectProperties(root).isNotEmpty ||
      customProperties.hasAtLeastOneProperty;

  Future<LockResponse> startEditing(List<String> linkedResources) async {
    status = EditStatus.starting;
    notifyListeners();
    try {
      final check = await repository.checkLock(view.uri);
      if (check.isLocked) {
        return check;
      }
      final acquired = await repository.acquireLock(view.uri, linkedResources);
      if (acquired.status == 'success') {
        status = EditStatus.editing;
        saved = false;
        _renewTimer = Timer.periodic(lockRenewalInterval, (_) => _renew());
      }
      return acquired;
    } finally {
      if (status == EditStatus.starting) {
        status = EditStatus.viewing;
      }
      notifyListeners();
    }
  }

  Future<void> _renew() async {
    try {
      await repository.renewLock(view.uri);
    } on LockLostException {
      if (!_disposed) {
        await stopEditing(release: false);
        onLockLost?.call();
      }
    }
  }

  Future<void> stopEditing({bool release = true}) async {
    _renewTimer?.cancel();
    _renewTimer = null;
    for (final group in groups) {
      group.reset();
    }
    customProperties.reset();
    status = EditStatus.viewing;
    notifyListeners();
    if (release) {
      await repository.releaseLock(view.uri);
    }
  }

  List<ValidationError> validate() {
    final errors = validateEntity(
      root,
      validationMessages,
      path: [view.typeLabel],
    );
    return errors;
  }

  List<Map<String, Object?>> buildChanges() {
    final changes = <Map<String, Object?>>[];
    final subject = view.uri;
    Map<String, Object?> base(String action, EditableGroup group) => {
      'action': action,
      'subject': subject,
      'predicate': group.group.property,
      'shape': group.group.objectShape,
      'entity_type': entityType,
      'entity_shape': view.shape,
    };
    for (final group in groups) {
      for (final value in group.existing) {
        if (value.markedForDeletion) {
          changes.add({
            ...base('delete', group),
            'object': value.triple.object,
            'newObject': null,
            if (group.group.isVirtual) 'is_virtual': true,
          });
        } else if (value.isModified) {
          changes.add({
            ...base('update', group),
            'object': value.triple.object,
            'newObject': value.newValue,
          });
        }
      }
      if (group.orderChanged) {
        changes.add({
          ...base('order', group),
          'object': group.currentOrder,
          'newObject': group.group.orderedBy,
        });
      }
    }
    final properties = collectProperties(root)
      ..addAll(collectCustomProperties(customProperties.properties));
    if (properties.isNotEmpty) {
      changes.add({
        'action': 'create',
        'subject': subject,
        'data': {'entity_type': entityType, 'properties': properties},
      });
    }
    return changes;
  }

  static List<Map<String, Object?>> deletionChanges(
    List<Map<String, Object?>> changes,
  ) => [
    for (final change in changes)
      if (change['action'] == 'delete' &&
          (change['predicate'] == null ||
              isValidUrl(change['object'].toString())))
        change,
  ];

  void setSaving({required bool saving}) {
    status = saving ? EditStatus.saving : EditStatus.editing;
    notifyListeners();
  }

  void markSaved() {
    saved = true;
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _renewTimer?.cancel();
    if (editing) {
      unawaited(repository.releaseLock(view.uri));
    }
    root.dispose();
    customProperties.dispose();
    for (final group in groups) {
      group.dispose();
    }
    super.dispose();
  }
}
