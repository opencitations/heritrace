// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../common/async_view.dart';
import '../common/dialogs.dart';
import '../common/primary_source_dialog.dart';
import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../form/collector.dart';
import '../form/form_model.dart';
import '../form/form_repository.dart';
import '../form/form_scope.dart';
import '../form/validator.dart';
import '../form/widgets/custom_properties_form.dart';
import '../form/widgets/entity_form.dart';
import '../form/widgets/validation_summary.dart';
import '../i18n/translations.g.dart';
import '../navigation/app_paths.dart';
import '../session/session_controller.dart';
import 'entity_repository.dart';

ValidationMessages validationMessages(Translations t) => ValidationMessages(
  required: t.ui.form.required,
  invalidUrl: t.ui.form.invalidUrl,
  invalidInput: (expected) => t.ui.form.invalidInput(expected: expected),
  tooMany: (name, count, max) =>
      t.ui.form.tooMany(name: name, count: count, max: max),
  tooFew: (name, count, min) =>
      t.ui.form.tooFew(name: name, count: count, min: min),
);

class CreateEntityPage extends ConsumerStatefulWidget {
  const CreateEntityPage({super.key});

  @override
  ConsumerState<CreateEntityPage> createState() => _CreateEntityPageState();
}

class _CreateEntityPageState extends ConsumerState<CreateEntityPage> {
  EntityTypeOption? _selectedType;
  EntityNode? _root;
  Object? _formError;
  bool _loadingForm = false;
  int _loadVersion = 0;
  final _custom = CustomPropertiesController();
  late final FormScopeController _scope = FormScopeController(rootLabel: '');

  @override
  void dispose() {
    _root?.dispose();
    _custom.dispose();
    _scope.dispose();
    super.dispose();
  }

  Future<void> _selectType(EntityTypeOption option) async {
    final version = ++_loadVersion;
    _scope.reset();
    _scope.rootLabel = option.label;
    _root?.removeListener(_revalidate);
    _root?.dispose();
    setState(() {
      _selectedType = option;
      _root = null;
      _loadingForm = true;
      _formError = null;
    });
    try {
      final fields = await ref
          .read(formRepositoryProvider)
          .formFields(option.entityClass, option.shape);
      if (version != _loadVersion || !mounted) {
        return;
      }
      final root = EntityNode(
        entityType: option.entityClass,
        entityShape: option.shape,
        fields: fields,
        depth: 0,
      );
      root.addListener(_revalidate);
      setState(() {
        _root = root;
        _loadingForm = false;
      });
    } on Exception catch (error) {
      if (version != _loadVersion || !mounted) {
        return;
      }
      setState(() {
        _formError = error;
        _loadingForm = false;
      });
    }
  }

  List<ValidationError> _collectErrors() {
    final t = Translations.of(context);
    final shacl = ref.read(sessionProvider).value!.config.shacl;
    if (!shacl) {
      return [
        if (!_custom.hasAtLeastOneProperty)
          ValidationError(
            message: t.ui.form.atLeastOneCustomProperty,
            path: [_scope.rootLabel],
          ),
      ];
    }
    final root = _root!;
    final errors = validateEntity(
      root,
      validationMessages(t),
      path: [_scope.rootLabel],
    );
    if (!hasAnyValue(root)) {
      errors.add(
        ValidationError(
          message: t.ui.form.atLeastOneProperty,
          path: [_scope.rootLabel],
        ),
      );
    }
    return errors;
  }

  void _revalidate() {
    _scope.setErrors(_collectErrors(), started: false);
  }

  Future<void> _submit() async {
    final t = Translations.of(context);
    final errors = _collectErrors();
    if (errors.isNotEmpty) {
      _scope.setErrors(errors);
      return;
    }
    final session = ref.read(sessionProvider).value!;
    final choice = await showPrimarySourceDialog(
      context,
      defaultPrimarySource: session.defaultPrimarySource,
    );
    if (choice == null || !mounted) {
      return;
    }
    final structuredData = session.config.shacl
        ? {
            'entity_type': _selectedType!.entityClass,
            'entity_shape': ?_selectedType!.shape,
            'properties': collectProperties(_root!),
          }
        : customCreationPayload(_custom.properties);
    String? uri;
    final ok = await runWithProgress(
      context,
      message: t.ui.create.validating,
      action: () async {
        uri = await ref
            .read(entityRepositoryProvider)
            .create(
              structuredData: structuredData,
              primarySource: choice.url,
              saveDefaultSource: choice.saveAsDefault,
            );
      },
    );
    if (!ok || !mounted) {
      return;
    }
    if (choice.saveAsDefault) {
      ref.read(sessionProvider.notifier).setDefaultPrimarySource(choice.url);
    }
    context.go(entityPath(uri!));
  }

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final session = ref.watch(sessionProvider).value!;
    final types = ref.watch(entityTypesProvider);
    final canSubmit = !session.config.shacl || _root != null;
    return FormScope(
      notifier: _scope,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    t.ui.create.title,
                    style: AppTextStyles.of(context).pageTitle,
                  ),
                  const SizedBox(height: appSectionSpacing),
                  if (session.config.shacl)
                    AsyncView(
                      value: types,
                      onRetry: () => ref.invalidate(entityTypesProvider),
                      builder: (options) {
                        if (_selectedType == null && options.isNotEmpty) {
                          WidgetsBinding.instance.addPostFrameCallback(
                            (_) => _selectType(options.first),
                          );
                        }
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            AppLabeledField(
                              label: t.ui.create.selectType,
                              child: AppMenuButton<EntityTypeOption?>(
                                value: _selectedType,
                                options: [
                                  for (final option in options)
                                    AppMenuOption(option, option.label),
                                ],
                                onChanged: (option) => _selectType(option!),
                              ),
                            ),
                            const SizedBox(height: appSectionSpacing),
                            if (_loadingForm)
                              const Center(child: CupertinoActivityIndicator())
                            else if (_formError != null)
                              ErrorView(
                                error: _formError!,
                                onRetry: () => _selectType(_selectedType!),
                              )
                            else if (_root != null)
                              EntityForm(node: _root!),
                          ],
                        );
                      },
                    )
                  else
                    CustomPropertiesForm(
                      controller: _custom,
                      datatypeOptions: session.config.datatypeOptions,
                    ),
                ],
              ),
            ),
          ),
          const ValidationSummary(),
          Padding(
            padding: const EdgeInsets.only(top: appInputSpacing),
            child: Align(
              alignment: Alignment.centerLeft,
              child: AppButton(
                variant: AppButtonVariant.filled,
                onPressed: canSubmit ? _submit : null,
                icon: CupertinoIcons.checkmark_circle,
                label: t.ui.create.submit,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
