// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:flutter/foundation.dart';

import '../api/api_exception.dart';
import '../form/collector.dart';
import '../form/field_def.dart';
import '../form/form_model.dart';
import '../form/server_errors.dart';
import '../form/validator.dart';
import '../form/widgets/custom_properties_form.dart';
import '../i18n/translations.g.dart';
import 'entity_models.dart';
import 'entity_repository.dart';

const lockRenewalInterval = Duration(seconds: 240);

/// A value whose text the user can change in edit mode.
abstract interface class EditedValue implements Listenable {
  String get newValue;
  void setValue(String value);
}

/// A value of a nested entity shown in place of the link, edited from the
/// page of the entity that links to it.
class DetailEdit extends ChangeNotifier implements EditedValue {
  DetailEdit({required this.subject, required this.field, required this.value})
    : newValue = value.value;

  final String subject;
  final FieldDef field;
  final DetailValue value;
  @override
  String newValue;
  bool markedForDeletion = false;

  bool get isModified => !markedForDeletion && newValue != value.value;

  @override
  void setValue(String value) {
    newValue = value;
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
    markedForDeletion = false;
    setValue(value.value);
  }
}

class ExistingValue extends ChangeNotifier implements EditedValue {
  ExistingValue({required this.triple, required this.group})
    : newValue = triple.value,
      newLanguage = triple.language,
      dateType = _dateTypeFor(triple.value) {
    for (final edit in detailEdits.values) {
      edit.addListener(notifyListeners);
    }
    final node = detailNode;
    if (node != null) {
      for (final group in node.groups) {
        group.keptCount = () => keptDetails(group.def).length;
      }
      node.addListener(notifyListeners);
    }
  }

  final EntityTriple triple;
  final PropertyGroup group;

  /// The values of the nested entity shown in place that the user can change:
  /// literals and IRIs typed by hand, not links to other entities.
  late final Map<DetailValue, DetailEdit> detailEdits = {
    if (triple.details case final details?)
      for (final detail in details)
        if (_detailField(detail.property) case final field?
            when field.hasValue == null)
          for (final value in detail.values)
            if (value.uri == null)
              value: DetailEdit(
                subject: triple.externalEntity!,
                field: field,
                value: value,
              ),
  };

  /// The fields of the nested entity that take several values typed by hand:
  /// the form adds new values to them, as it does for a field of the entity.
  late final EntityNode? detailNode = switch ({
    for (final edit in detailEdits.values)
      if (edit.field.max != 1) edit.field,
  }) {
    final fields when fields.isNotEmpty => EntityNode(
      entityType: fields.first.entityType!,
      entityShape: fields.first.subjectShape,
      fields: fields.toList(),
      depth: 1,
      fillMinimum: false,
    ),
    _ => null,
  };

  Iterable<DetailEdit> keptDetails(FieldDef field) => detailEdits.values.where(
    (edit) => edit.field == field && !edit.markedForDeletion,
  );

  /// Whether the user can remove [edit]: its field takes several values, and
  /// the values left still reach the minimum of the field.
  bool canDeleteDetail(DetailEdit edit) {
    final group = detailGroup(edit.field);
    return group != null &&
        keptDetails(edit.field).length + group.items.length > edit.field.min;
  }

  FieldGroup? detailGroup(FieldDef field) =>
      detailNode?.groups.where((group) => group.def == field).firstOrNull;

  FieldDef? _detailField(String property) {
    final field = group.field;
    final fields = [
      ...?field?.nestedShape,
      for (final alternative in field?.or ?? const <FieldDef>[])
        ...?alternative.nestedShape,
    ];
    return fields
        .where(
          (nested) =>
              nested.uri == property &&
              nested.subjectShape == triple.detailsShape,
        )
        .firstOrNull;
  }

  @override
  String newValue;
  String? newLanguage;
  DateType dateType;
  bool markedForDeletion = false;

  bool get isModified =>
      newValue != triple.value || newLanguage != triple.language;

  Iterable<DetailEdit> get modifiedDetails =>
      detailEdits.values.where((edit) => edit.isModified);

  Iterable<DetailEdit> get deletedDetails =>
      detailEdits.values.where((edit) => edit.markedForDeletion);

  Map<String, List<Object>> get newDetails =>
      collectGroups(detailNode?.groups ?? const []);

  bool get detailsChanged =>
      modifiedDetails.isNotEmpty ||
      deletedDetails.isNotEmpty ||
      newDetails.isNotEmpty;

  bool get isEntityLink => triple.externalEntity != null;

  static DateType _dateTypeFor(String value) => switch (value.length) {
    7 => DateType.month,
    4 => DateType.year,
    _ => DateType.date,
  };

  @override
  void setValue(String value) {
    newValue = value;
    notifyListeners();
  }

  void setLanguage(String? language) {
    newLanguage = language;
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
    newLanguage = triple.language;
    dateType = _dateTypeFor(triple.value);
    markedForDeletion = false;
    for (final edit in detailEdits.values) {
      edit.reset();
    }
    for (final group in detailNode?.groups ?? const <FieldGroup>[]) {
      for (final item in [...group.items]) {
        group.removeItem(item);
      }
    }
    notifyListeners();
  }

  @override
  void dispose() {
    for (final edit in detailEdits.values) {
      edit.dispose();
    }
    detailNode?.dispose();
    super.dispose();
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
    formGroup?.savedLanguages = () => [
      for (final value in existing)
        if (!value.markedForDeletion) value.newLanguage,
    ];
    formGroup?.keptCount = () =>
        existing.where((value) => !value.markedForDeletion).length;
    formGroup?.savedItemFields = () => [
      for (final value in existing)
        if (!value.markedForDeletion)
          for (final detail in value.triple.details ?? const <EntityDetail>[])
            detail.property,
    ];
    formGroup?.addListener(notifyListeners);
  }

  /// The languages of the values of this group other than [except]; null
  /// stands for a value without a language.
  Set<String?> usedLanguages(ExistingValue except) => {
    for (final value in existing)
      if (value != except && !value.markedForDeletion) value.newLanguage,
    for (final item in formGroup?.items ?? const <FormItem>[])
      if (item is LiteralItem) item.language,
  };

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
      if (item.tempId != null && collectItem(item) != null) item.tempId!,
  ];

  bool get orderChanged =>
      group.orderedBy != null && !listEquals(originalOrder, currentOrder);

  bool get isSwitchedOn =>
      existing.any(
        (value) => !value.markedForDeletion && isTrueLiteral(value.newValue),
      ) ||
      (formGroup?.isSwitchedOn ?? false);

  bool get canSwitch => existing.isNotEmpty || formGroup != null;

  bool get hasContent =>
      existing.any(
        (value) => !value.markedForDeletion && value.newValue.trim().isNotEmpty,
      ) ||
      (formGroup?.hasContent ?? false);

  void switchTo(bool on) {
    if (existing.isEmpty) {
      formGroup!.switchTo(on);
      return;
    }
    final value = existing.single;
    if (isTrueLiteral(value.triple.value) == on) {
      value.reset();
    } else if (on) {
      value.setValue('true');
    } else {
      value.markForDeletion();
    }
  }

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
  Timer? _renewTimer;
  bool _disposed = false;
  void Function()? onLockLost;

  bool get editing =>
      status == EditStatus.editing || status == EditStatus.saving;

  bool get showsCustomProperties => !view.shacl || !view.hasFormFields;

  /// Whether [group] applies, given the values its `shownWith` and
  /// `excludedWith` fields hold.
  bool applies(EditableGroup group) {
    final field = group.group.field;
    if (field == null) return true;
    bool hasContent(List<String> properties) => groups.any(
      (other) => properties.contains(other.group.property) && other.hasContent,
    );
    return (field.shownWith.isEmpty || hasContent(field.shownWith)) &&
        (group.hasContent || !hasContent(field.excludedWith));
  }

  bool get hasChanges =>
      groups.any(
        (group) =>
            group.existing.any(
              (v) => v.isModified || v.markedForDeletion || v.detailsChanged,
            ) ||
            group.orderChanged,
      ) ||
      _newProperties().isNotEmpty ||
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
    return [
      ...validateEntity(root, validationMessages, path: [view.typeLabel]),
      for (final group in groups)
        if (applies(group))
          for (final value in group.existing)
            if (value.detailNode case final node? when !value.markedForDeletion)
              ...validateEntity(
                node,
                validationMessages,
                path: [view.typeLabel, group.group.displayName],
              ),
    ];
  }

  /// The errors of a rejected save, each beside the value or in the field it
  /// concerns, whether that belongs to this resource, to a nested resource
  /// shown in place or to a new one.
  List<ValidationError> serverErrors(
    Translations t,
    List<ServerFieldError> errors,
  ) {
    final path = [view.typeLabel];
    final FormNode own = (node: root, path: path);
    final shownInPlace = <String, FormNode>{
      for (final group in groups)
        for (final value in group.existing)
          if (value.detailNode case final node?)
            value.triple.externalEntity!: (
              node: node,
              path: [...path, group.group.displayName],
            ),
    };
    final created = {
      ...nestedNodes(own),
      for (final at in shownInPlace.values) ...nestedNodes(at),
    };
    ValidationError place(ServerFieldError error) {
      final at = error.subject == view.uri
          ? own
          : created[error.subject] ?? shownInPlace[error.subject];
      return _savedValueError(t, error) ??
          (at == null ? null : errorInNode(t, at, error)) ??
          unplacedError(t, error, path);
    }

    return [for (final error in errors) place(error)];
  }

  /// The error beside a saved value: the one the error rejects, or the only
  /// value of the field.
  ValidationError? _savedValueError(Translations t, ServerFieldError error) {
    for (final group in groups) {
      final values = <({EditedValue value, String name, List<String> path})>[
        if (error.subject == view.uri &&
            group.group.property == error.predicate)
          for (final value in group.existing)
            if (!value.markedForDeletion)
              (
                value: value,
                name: group.group.displayName,
                path: [view.typeLabel],
              ),
        for (final value in group.existing)
          if (value.triple.externalEntity == error.subject)
            for (final edit in value.detailEdits.values)
              if (edit.field.uri == error.predicate && !edit.markedForDeletion)
                (
                  value: edit,
                  name: edit.field.displayName,
                  path: [view.typeLabel, group.group.displayName],
                ),
      ];
      final input = error.input;
      final match = input == null
          ? values.singleOrNull
          : values.where((value) => value.value.newValue == input).firstOrNull;
      if (match != null) {
        return ValidationError(
          message: describeServerError(t, error, match.name),
          path: match.path,
          value: match.value,
          fieldName: match.name,
        );
      }
    }
    return null;
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
      final dropped = !applies(group);
      for (final value in group.existing) {
        if (dropped || value.markedForDeletion) {
          changes.add({
            ...base('delete', group),
            'object': value.triple.object,
            'newObject': null,
            'language': ?value.triple.language,
          });
        } else if (value.isModified) {
          changes.add({
            ...base('update', group),
            'object': value.triple.object,
            'newObject': value.newValue,
            'language': ?value.triple.language,
            if (group.group.field?.withLanguage ?? false)
              'newLanguage': value.newLanguage ?? '',
          });
        }
        if (!dropped && !value.markedForDeletion) {
          Map<String, Object?> detail(String action, DetailEdit edit) => {
            'action': action,
            'subject': edit.subject,
            'predicate': edit.field.uri,
            'entity_type': edit.field.entityType,
            'entity_shape': edit.field.subjectShape,
            'object': edit.value.value,
            'language': ?edit.value.language,
          };
          for (final edit in value.deletedDetails) {
            changes.add({...detail('delete', edit), 'newObject': null});
          }
          for (final edit in value.modifiedDetails) {
            changes.add({
              ...detail('update', edit),
              'newObject': edit.newValue,
            });
          }
          if (value.newDetails case final properties
              when properties.isNotEmpty) {
            changes.add({
              'action': 'create',
              'subject': value.triple.externalEntity,
              'data': {
                'entity_type': value.detailNode!.entityType,
                'properties': properties,
              },
            });
          }
        }
      }
      if (!dropped && group.orderChanged) {
        changes.add({
          ...base('order', group),
          'object': group.currentOrder,
          'newObject': group.group.orderedBy,
        });
      }
    }
    final properties = _newProperties()
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

  /// The values added through the form, for the groups that apply. The
  /// session decides, since the fields that show a group may hold only
  /// existing values, which the form does not know.
  Map<String, List<Object>> _newProperties() => collectGroups([
    for (final group in groups)
      if (group.formGroup != null && applies(group)) group.formGroup!,
  ]);

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
