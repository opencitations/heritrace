// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import 'app_theme.dart';
import 'spacing.dart';

enum AppButtonVariant { filled, tinted, plain }

class AppButton extends StatelessWidget {
  const AppButton({
    required this.label,
    required this.onPressed,
    this.icon,
    this.variant = AppButtonVariant.plain,
    this.destructive = false,
    this.focusNode,
    super.key,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final AppButtonVariant variant;
  final bool destructive;
  final FocusNode? focusNode;

  @override
  Widget build(BuildContext context) {
    final color = destructive ? AppColors.error : null;
    final foreground = destructive && onPressed != null
        ? (variant == AppButtonVariant.filled ? null : AppColors.error)
        : null;
    final text = Text(label, overflow: TextOverflow.ellipsis);
    final child = icon == null ? text : IconLabel(icon: icon!, label: text);
    return switch (variant) {
      AppButtonVariant.filled => CupertinoButton.filled(
        sizeStyle: CupertinoButtonSize.medium,
        color: color,
        foregroundColor: onPressed == null ? CupertinoColors.systemGrey : null,
        focusNode: focusNode,
        onPressed: onPressed,
        child: child,
      ),
      AppButtonVariant.tinted => CupertinoButton.tinted(
        sizeStyle: CupertinoButtonSize.medium,
        color: color,
        foregroundColor: foreground,
        focusNode: focusNode,
        onPressed: onPressed,
        child: child,
      ),
      AppButtonVariant.plain => CupertinoButton(
        sizeStyle: CupertinoButtonSize.medium,
        padding: const EdgeInsets.symmetric(vertical: appInputSpacing / 2),
        foregroundColor: foreground,
        focusNode: focusNode,
        onPressed: onPressed,
        child: child,
      ),
    };
  }
}

class AppIconButton extends StatelessWidget {
  const AppIconButton({
    required this.icon,
    required this.label,
    required this.onPressed,
    this.color,
    super.key,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      button: true,
      excludeSemantics: true,
      child: CupertinoButton(
        sizeStyle: CupertinoButtonSize.small,
        foregroundColor: onPressed == null ? null : color,
        onPressed: onPressed,
        child: Icon(icon, size: 20),
      ),
    );
  }
}

BoxDecoration _fieldDecoration({required bool hasError}) => BoxDecoration(
  color: AppColors.fieldFill,
  borderRadius: BorderRadius.circular(appRadius),
  border: hasError ? Border.all(color: AppColors.error) : null,
);

const _fieldPadding = EdgeInsets.symmetric(horizontal: 10, vertical: 10);

class _WithError extends StatelessWidget {
  const _WithError({required this.errorText, required this.child});

  final String? errorText;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (errorText == null) {
      return child;
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        child,
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            errorText!,
            style: AppTextStyles.of(context).caption
                .copyWith(color: AppColors.error),
          ),
        ),
      ],
    );
  }
}

class AppTextField extends StatelessWidget {
  const AppTextField({
    this.controller,
    this.focusNode,
    this.placeholder,
    this.errorText,
    this.maxLines = 1,
    this.keyboardType,
    this.onChanged,
    this.onSubmitted,
    this.suffix,
    this.autofocus = false,
    super.key,
  });

  final TextEditingController? controller;
  final FocusNode? focusNode;
  final String? placeholder;
  final String? errorText;
  final int maxLines;
  final TextInputType? keyboardType;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final Widget? suffix;
  final bool autofocus;

  @override
  Widget build(BuildContext context) {
    return _WithError(
      errorText: errorText,
      child: CupertinoTextField(
        controller: controller,
        focusNode: focusNode,
        placeholder: placeholder,
        maxLines: maxLines,
        keyboardType: keyboardType,
        onChanged: onChanged,
        onSubmitted: onSubmitted,
        suffix: suffix,
        autofocus: autofocus,
        padding: _fieldPadding,
        decoration: _fieldDecoration(hasError: errorText != null),
      ),
    );
  }
}

class AppMenuOption<T> {
  const AppMenuOption(this.value, this.label);

  final T value;
  final String label;
}

/// An iOS pop-up button: it shows the chosen option and opens a pull-down
/// menu with all the options.
class AppMenuButton<T> extends StatelessWidget {
  const AppMenuButton({
    required this.value,
    required this.options,
    required this.onChanged,
    this.placeholder,
    this.errorText,
    this.focusNode,
    super.key,
  });

  final T value;
  final List<AppMenuOption<T>> options;
  final ValueChanged<T> onChanged;
  final String? placeholder;
  final String? errorText;
  final FocusNode? focusNode;

  @override
  Widget build(BuildContext context) {
    final styles = AppTextStyles.of(context);
    final selected = options.where((o) => o.value == value).firstOrNull;
    return _WithError(
      errorText: errorText,
      child: CupertinoMenuAnchor(
        childFocusNode: focusNode,
        menuChildren: [
          for (final option in options)
            CupertinoMenuItem(
              onPressed: () => onChanged(option.value),
              trailing: option.value == value
                  ? const Icon(CupertinoIcons.check_mark, size: 18)
                  : null,
              child: Text(option.label),
            ),
        ],
        builder: (context, controller, _) => GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () =>
              controller.isOpen ? controller.close() : controller.open(),
          child: Focus(
            focusNode: focusNode,
            child: Container(
              padding: _fieldPadding,
              decoration: _fieldDecoration(hasError: errorText != null),
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final label = Text(
                    selected?.label ?? placeholder ?? '',
                    overflow: TextOverflow.ellipsis,
                    style: selected == null
                        ? styles.body.copyWith(color: AppColors.secondaryText)
                        : styles.body,
                  );
                  return Row(
                    mainAxisSize: constraints.hasBoundedWidth
                        ? MainAxisSize.max
                        : MainAxisSize.min,
                    children: [
                      if (constraints.hasBoundedWidth)
                        Expanded(child: label)
                      else
                        Flexible(child: label),
                      const SizedBox(width: appInputSpacing / 2),
                      const Icon(
                        CupertinoIcons.chevron_up_chevron_down,
                        size: 16,
                        color: AppColors.secondaryText,
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// A rounded white group on the grey page background, as in iOS Settings.
class AppSection extends StatelessWidget {
  const AppSection({required this.children, super.key});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return CupertinoListSection.insetGrouped(
      margin: EdgeInsets.zero,
      hasLeading: false,
      children: children,
    );
  }
}

/// [AppSection] with a single padded body.
class AppCard extends StatelessWidget {
  const AppCard({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AppSection(
      children: [
        Padding(padding: const EdgeInsets.all(appCardPadding), child: child),
      ],
    );
  }
}

class AppLabeledField extends StatelessWidget {
  const AppLabeledField({required this.label, required this.child, super.key});

  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(label, style: AppTextStyles.of(context).caption),
        const SizedBox(height: 4),
        child,
      ],
    );
  }
}

class AppTooltip extends StatelessWidget {
  const AppTooltip({required this.message, required this.child, super.key});

  final String message;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return RawTooltip(
      semanticsTooltip: message,
      triggerMode: TooltipTriggerMode.tap,
      hoverDelay: const Duration(milliseconds: 300),
      tooltipBuilder: (context, animation) => FadeTransition(
        opacity: animation,
        child: Container(
          constraints: const BoxConstraints(maxWidth: 320),
          padding: const EdgeInsets.symmetric(
            horizontal: appInputSpacing,
            vertical: appInputSpacing / 2,
          ),
          decoration: BoxDecoration(
            color: AppColors.tooltip,
            borderRadius: BorderRadius.circular(appRadius),
          ),
          child: Text(
            message,
            style: AppTextStyles.of(context).caption
                .copyWith(color: AppColors.onTooltip),
          ),
        ),
      ),
      child: child,
    );
  }
}

class AppBanner extends StatelessWidget {
  const AppBanner({
    required this.text,
    this.icon = CupertinoIcons.info_circle,
    this.error = false,
    super.key,
  });

  final String text;
  final IconData icon;
  final bool error;

  @override
  Widget build(BuildContext context) {
    final color = error ? AppColors.error : AppColors.primary;
    return Container(
      padding: const EdgeInsets.all(appCardPadding),
      decoration: BoxDecoration(
        color: error ? AppColors.errorTint : AppColors.primaryTint,
        borderRadius: BorderRadius.circular(appRadius),
      ),
      child: IconLabel(
        icon: icon,
        color: color,
        expand: true,
        label: Text(text),
      ),
    );
  }
}

class AppSelectable extends StatelessWidget {
  const AppSelectable({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) => SelectableRegion(
    selectionControls: cupertinoTextSelectionHandleControls,
    child: child,
  );
}

class DragHandle extends StatelessWidget {
  const DragHandle({required this.index, super.key});

  final int index;

  @override
  Widget build(BuildContext context) => ReorderableDragStartListener(
    index: index,
    child: const MouseRegion(
      cursor: SystemMouseCursors.grab,
      child: Icon(
        CupertinoIcons.line_horizontal_3,
        color: AppColors.secondaryText,
      ),
    ),
  );
}

/// List tile text that wraps instead of being cut to one line, because
/// record labels are long and must be read in full.
class TileText extends StatelessWidget {
  const TileText(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) =>
      Text(text, maxLines: 4, overflow: TextOverflow.ellipsis);
}

/// A list tile with vertical padding, so that [TileText] spanning several
/// lines keeps its distance from the separators.
class AppListTile extends StatelessWidget {
  const AppListTile({
    required this.title,
    this.subtitle,
    this.additionalInfo,
    this.trailing,
    this.onTap,
    super.key,
  });

  final Widget title;
  final Widget? subtitle;
  final Widget? additionalInfo;
  final Widget? trailing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => CupertinoListTile(
    padding: const EdgeInsetsDirectional.fromSTEB(20, 10, 14, 10),
    title: title,
    subtitle: subtitle,
    additionalInfo: additionalInfo,
    trailing: trailing,
    onTap: onTap,
  );
}

/// An icon with the point size of the text next to it. CupertinoIcons
/// glyphs, like SF Symbols, are drawn to sit centred on the capital letters
/// when they share the baseline of the text, so place it in a row aligned on
/// [TextBaseline.alphabetic].
class TextIcon extends StatelessWidget {
  const TextIcon(this.icon, {this.style, this.color, super.key});

  final IconData icon;
  final TextStyle? style;
  final Color? color;

  @override
  Widget build(BuildContext context) => Icon(
    icon,
    size: DefaultTextStyle.of(context).style.merge(style).fontSize,
    color: color,
  );
}

/// A [TextIcon] before a label. A label on several lines keeps the icon on
/// its first line.
class IconLabel extends StatelessWidget {
  const IconLabel({
    required this.icon,
    required this.label,
    this.style,
    this.color,
    this.expand = false,
    super.key,
  });

  final IconData icon;
  final Widget label;
  final TextStyle? style;
  final Color? color;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final text = DefaultTextStyle.merge(style: style, child: label);
    return Row(
      mainAxisSize: expand ? MainAxisSize.max : MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.baseline,
      textBaseline: TextBaseline.alphabetic,
      children: [
        TextIcon(icon, style: style, color: color),
        const SizedBox(width: appInputSpacing / 2),
        if (expand) Expanded(child: text) else Flexible(child: text),
      ],
    );
  }
}

class AppBreadcrumb {
  const AppBreadcrumb(this.label, {this.onPressed, this.style});

  final String label;
  final VoidCallback? onPressed;
  final TextStyle? style;
}

/// The path to the current page, which is the last crumb. Every crumb is as
/// tall as a button, so the trail keeps its height whatever the crumbs are.
class AppBreadcrumbs extends StatelessWidget {
  const AppBreadcrumbs({required this.crumbs, super.key});

  final List<AppBreadcrumb> crumbs;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        for (final (index, crumb) in crumbs.indexed) ...[
          if (index > 0)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: appInputSpacing / 2),
              child: Icon(
                CupertinoIcons.chevron_right,
                size: 16,
                color: AppColors.secondaryText,
              ),
            ),
          if (crumb.onPressed == null)
            ConstrainedBox(
              constraints: const BoxConstraints(
                minHeight: kMinInteractiveDimensionCupertino,
              ),
              child: Align(
                widthFactor: 1,
                child: Text(crumb.label, style: crumb.style),
              ),
            )
          else
            CupertinoButton(
              padding: EdgeInsets.zero,
              minimumSize: const Size(0, kMinInteractiveDimensionCupertino),
              onPressed: crumb.onPressed,
              child: Text(crumb.label, style: crumb.style),
            ),
        ],
      ],
    );
  }
}

/// The margin around page content. A scroll view takes it as its padding, so
/// that its scrollbar runs in the margin instead of over the content.
EdgeInsets pageMargin(BuildContext context) => EdgeInsets.all(
  MediaQuery.sizeOf(context).width < appCompactWidth
      ? appCardPadding
      : appPageMargin,
);

/// Spaces the items of a vertical list, leaving no gap above the first one.
EdgeInsets listItemSpacing(int index) =>
    EdgeInsets.only(top: index == 0 ? 0 : appInputSpacing);

/// A dialog wide enough for lists and form fields, with left-aligned content.
class AppDialog extends StatelessWidget {
  const AppDialog({
    required this.content,
    this.title,
    this.actions = const [],
    super.key,
  });

  final String? title;
  final Widget content;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    final styles = AppTextStyles.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(appCardPadding),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: CupertinoPopupSurface(
            child: DefaultTextStyle(
              style: styles.body,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Flexible(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.all(appSectionSpacing),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          if (title != null) ...[
                            Text(title!, style: styles.heading),
                            const SizedBox(height: appInputSpacing),
                          ],
                          content,
                        ],
                      ),
                    ),
                  ),
                  if (actions.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(
                        appSectionSpacing,
                        0,
                        appSectionSpacing,
                        appSectionSpacing,
                      ),
                      child: Wrap(
                        alignment: WrapAlignment.end,
                        spacing: appInputSpacing / 2,
                        runSpacing: appInputSpacing / 2,
                        children: actions,
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
