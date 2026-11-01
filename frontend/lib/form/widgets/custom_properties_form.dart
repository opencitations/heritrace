// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../design/app_theme.dart';
import '../../design/controls.dart';
import '../../design/spacing.dart';
import '../../i18n/translations.g.dart';
import '../../session/session_models.dart';
import '../form_model.dart';
import '../form_repository.dart';
import '../validator.dart';

class CustomPropertiesController extends ChangeNotifier {
  final List<CustomProperty> properties = [];

  void add() {
    final property = CustomProperty();
    property.addListener(notifyListeners);
    properties.add(property);
    notifyListeners();
  }

  void remove(CustomProperty property) {
    properties.remove(property);
    property.dispose();
    notifyListeners();
  }

  void reset() {
    for (final property in properties) {
      property.dispose();
    }
    properties.clear();
    notifyListeners();
  }

  bool get hasAtLeastOneProperty => properties.any((p) => p.isComplete);
}

class CustomPropertiesForm extends ConsumerWidget {
  const CustomPropertiesForm({
    required this.controller,
    required this.datatypeOptions,
    super.key,
  });

  final CustomPropertiesController controller;
  final List<DatatypeOption> datatypeOptions;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final property in controller.properties)
            Padding(
              key: ObjectKey(property),
              padding: const EdgeInsets.only(bottom: appSectionSpacing),
              child: AppCard(
                child: _CustomPropertyRow(
                  property: property,
                  datatypeOptions: datatypeOptions,
                  onRemove: () => controller.remove(property),
                ),
              ),
            ),
          Align(
            alignment: Alignment.centerLeft,
            child: AppButton(
              onPressed: controller.add,
              icon: CupertinoIcons.add_circled,
              label: t.ui.form.addProperty,
            ),
          ),
        ],
      ),
    );
  }
}

class _CustomPropertyRow extends ConsumerStatefulWidget {
  const _CustomPropertyRow({
    required this.property,
    required this.datatypeOptions,
    required this.onRemove,
  });

  final CustomProperty property;
  final List<DatatypeOption> datatypeOptions;
  final VoidCallback onRemove;

  @override
  ConsumerState<_CustomPropertyRow> createState() => _CustomPropertyRowState();
}

class _CustomPropertyRowState extends ConsumerState<_CustomPropertyRow> {
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  void _refreshDatatypes() {
    final property = widget.property;
    final value = property.value;
    _debounce?.cancel();
    if (property.type != 'literal' || value.trim().isEmpty) {
      property.setValidDatatypes(null);
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 300), () async {
      final valid = await ref
          .read(formRepositoryProvider)
          .validDatatypes(value);
      if (mounted && property.value == value && property.type == 'literal') {
        property.setValidDatatypes(valid);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final property = widget.property;
    final title = property.predicate.trim().isEmpty
        ? t.ui.form.customProperty
        : readablePredicate(property.predicate);
    final valid = property.validDatatypes;
    final options = valid == null
        ? widget.datatypeOptions
        : widget.datatypeOptions
              .where((option) => valid.contains(option.uri))
              .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            RemoveButton(
              label: t.ui.actions.delete,
              onPressed: widget.onRemove,
            ),
            Expanded(
              child: Text(title, style: AppTextStyles.of(context).heading),
            ),
          ],
        ),
        const SizedBox(height: appInputSpacing / 2),
        AppTextField(
          placeholder: t.ui.form.propertyUri,
          errorText:
              property.predicate.trim().isNotEmpty &&
                  !isValidUrl(property.predicate.trim())
              ? t.ui.form.invalidPropertyUri
              : null,
          keyboardType: TextInputType.url,
          onChanged: (value) => property.update(predicate: value),
        ),
        const SizedBox(height: appInputSpacing),
        AppTextField(
          placeholder: t.ui.form.value,
          errorText:
              property.type == 'uri' &&
                  property.value.trim().isNotEmpty &&
                  !isValidUrl(property.value.trim())
              ? t.ui.form.invalidUrl
              : null,
          onChanged: (value) {
            property.update(value: value);
            _refreshDatatypes();
          },
        ),
        const SizedBox(height: appInputSpacing),
        Row(
          children: [
            Expanded(
              child: AppLabeledField(
                label: t.ui.form.valueType,
                child: AppMenuButton<String>(
                  value: property.type,
                  options: [
                    AppMenuOption('literal', t.ui.form.literal),
                    AppMenuOption('uri', t.ui.form.uri),
                  ],
                  onChanged: (type) {
                    property.update(type: type);
                    _refreshDatatypes();
                  },
                ),
              ),
            ),
            if (property.type == 'literal') ...[
              const SizedBox(width: appInputSpacing),
              Expanded(
                child: AppLabeledField(
                  label: t.ui.form.datatype,
                  child: AppMenuButton<String?>(
                    value:
                        options.any((option) => option.uri == property.datatype)
                        ? property.datatype
                        : options.firstOrNull?.uri,
                    errorText: options.isEmpty
                        ? t.ui.form.noValidDatatypes
                        : null,
                    options: [
                      for (final option in options)
                        AppMenuOption(option.uri, option.label),
                    ],
                    onChanged: (datatype) =>
                        property.update(datatype: datatype),
                  ),
                ),
              ),
            ],
          ],
        ),
      ],
    );
  }
}

String readablePredicate(String uri) {
  final parsed = Uri.tryParse(uri.trim());
  if (parsed == null) {
    return uri;
  }
  var last = parsed.fragment;
  if (last.isEmpty) {
    final segments = parsed.pathSegments.where((s) => s.isNotEmpty).toList();
    last = segments.isEmpty
        ? parsed.host.replaceFirst('www.', '')
        : segments.last;
  }
  return last
      .replaceAllMapped(
        RegExp(r'([a-z])([A-Z])'),
        (m) => '${m.group(1)} ${m.group(2)}',
      )
      .replaceAll(RegExp(r'[_\-.]'), ' ')
      .toLowerCase()
      .trim();
}
