// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import 'app_theme.dart';
import 'spacing.dart';

enum AppButtonVariant { filled, tinted, plain }

/// The smallest area a finger can reliably hit, 44 × 44 pt in iOS.
const minTapTarget = Size.square(kMinInteractiveDimensionCupertino);

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
    final color = destructive ? AppColors.of(context).error : null;
    final foreground = destructive && onPressed != null
        ? (variant == AppButtonVariant.filled
              ? null
              : AppColors.of(context).error)
        : null;
    final text = Text(label, overflow: TextOverflow.ellipsis);
    final child = SelectionContainer.disabled(
      child: icon == null ? text : IconLabel(icon: icon!, label: text),
    );
    return switch (variant) {
      AppButtonVariant.filled => CupertinoButton.filled(
        sizeStyle: CupertinoButtonSize.medium,
        minimumSize: minTapTarget,
        color: color,
        foregroundColor: onPressed == null
            ? AppColors.of(context).disabled
            : null,
        focusNode: focusNode,
        onPressed: onPressed,
        child: child,
      ),
      AppButtonVariant.tinted => CupertinoButton.tinted(
        sizeStyle: CupertinoButtonSize.medium,
        minimumSize: minTapTarget,
        color: color,
        foregroundColor: foreground,
        focusNode: focusNode,
        onPressed: onPressed,
        child: child,
      ),
      AppButtonVariant.plain => CupertinoButton(
        sizeStyle: CupertinoButtonSize.medium,
        minimumSize: minTapTarget,
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
        minimumSize: minTapTarget,
        foregroundColor: onPressed == null ? null : color,
        onPressed: onPressed,
        child: Icon(icon, size: 20),
      ),
    );
  }
}

BoxDecoration _fieldDecoration(
  BuildContext context, {
  required bool hasError,
}) => BoxDecoration(
  color: AppColors.of(context).fieldFill,
  borderRadius: BorderRadius.circular(appRadius),
  border: hasError ? Border.all(color: AppColors.of(context).error) : null,
);

const _fieldPadding = EdgeInsets.symmetric(horizontal: 10, vertical: 12);

/// A short line under a field: a hint, or an error when [error].
class FieldCaption extends StatelessWidget {
  const FieldCaption(this.text, {this.error = false, super.key});

  final String text;
  final bool error;

  @override
  Widget build(BuildContext context) {
    final caption = AppTextStyles.of(context).caption;
    return Padding(
      padding: const EdgeInsets.only(top: appCaptionSpacing),
      child: Text(
        text,
        style: error
            ? caption.copyWith(color: AppColors.of(context).error)
            : caption,
      ),
    );
  }
}

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
      children: [child, FieldCaption(errorText!, error: true)],
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
        decoration: _fieldDecoration(context, hasError: errorText != null),
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
      child: SelectionContainer.disabled(
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
                decoration: _fieldDecoration(
                  context,
                  hasError: errorText != null,
                ),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final label = Text(
                      selected?.label ?? placeholder ?? '',
                      overflow: TextOverflow.ellipsis,
                      style: selected == null
                          ? styles.body.copyWith(
                              color: AppColors.of(context).secondaryText,
                            )
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
                        Icon(
                          CupertinoIcons.chevron_up_chevron_down,
                          size: 16,
                          color: AppColors.of(context).secondaryText,
                        ),
                      ],
                    );
                  },
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Where tile text starts; section dividers start at the same offset.
const double _tileTextInset = 20;

/// A button at the leading edge of a row in edit mode. Its icon starts where
/// the row's text would, so it lines up with the add buttons below the rows.
class RowLeadingButton extends StatelessWidget {
  const RowLeadingButton({
    required this.icon,
    required this.label,
    required this.onPressed,
    this.color,
    super.key,
  });

  final IconData icon;
  final String label;
  final VoidCallback onPressed;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      button: true,
      excludeSemantics: true,
      child: CupertinoButton(
        padding: EdgeInsets.zero,
        minimumSize: minTapTarget,
        alignment: AlignmentDirectional.centerStart,
        foregroundColor: color,
        onPressed: onPressed,
        child: Icon(icon, size: 20),
      ),
    );
  }
}

/// The red minus that removes a row in edit mode, as in iOS lists.
class RemoveButton extends StatelessWidget {
  const RemoveButton({required this.label, required this.onPressed, super.key});

  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => RowLeadingButton(
    icon: CupertinoIcons.minus_circle_fill,
    label: label,
    color: AppColors.of(context).error,
    onPressed: onPressed,
  );
}

/// A rounded white group on the grey page background, as in iOS Settings,
/// with its [header] above it and its [footer] below, lined up with the
/// group's content.
class AppSection extends StatelessWidget {
  const AppSection({
    required this.children,
    this.header,
    this.footer,
    super.key,
  });

  final List<Widget> children;
  final Widget? header;
  final String? footer;

  @override
  Widget build(BuildContext context) {
    final section = CupertinoListSection.insetGrouped(
      margin: EdgeInsets.zero,
      dividerMargin: _tileTextInset,
      additionalDividerMargin: 0,
      children: children,
    );
    if (header == null && footer == null) {
      return section;
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (header != null)
          Padding(
            padding: const EdgeInsets.only(left: appCardPadding, bottom: 6),
            child: header,
          ),
        section,
        if (footer != null)
          Padding(
            padding: const EdgeInsets.only(
              left: appCardPadding,
              right: appCardPadding,
              top: 6,
            ),
            child: Text(footer!, style: AppTextStyles.of(context).caption),
          ),
      ],
    );
  }
}

/// [AppSection] with a single padded body.
class AppCard extends StatelessWidget {
  const AppCard({required this.child, this.header, this.footer, super.key});

  final Widget child;
  final Widget? header;
  final String? footer;

  @override
  Widget build(BuildContext context) {
    return AppSection(
      header: header,
      footer: footer,
      children: [
        SizedBox(
          width: double.infinity,
          child: Padding(
            padding: const EdgeInsets.all(appCardPadding),
            child: child,
          ),
        ),
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
            color: AppColors.of(context).tooltip,
            borderRadius: BorderRadius.circular(appRadius),
          ),
          child: Text(
            message,
            style: AppTextStyles.of(context).caption
                .copyWith(color: AppColors.of(context).onTooltip),
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
    final color = error ? AppColors.of(context).error : AppColors.primary;
    return Container(
      padding: const EdgeInsets.all(appCardPadding),
      decoration: BoxDecoration(
        color: error ? AppColors.of(context).errorTint : AppColors.primaryTint,
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

class DragHandle extends StatelessWidget {
  const DragHandle({required this.index, super.key});

  final int index;

  @override
  Widget build(BuildContext context) => ReorderableDragStartListener(
    index: index,
    child: MouseRegion(
      cursor: SystemMouseCursors.grab,
      child: SizedBox.fromSize(
        size: minTapTarget,
        child: Icon(
          CupertinoIcons.line_horizontal_3,
          color: AppColors.of(context).secondaryText,
        ),
      ),
    ),
  );
}

/// A page or section title, which screen readers announce as a heading.
class AppHeading extends StatelessWidget {
  const AppHeading(this.text, {required this.style, this.textAlign, super.key});

  final String text;
  final TextStyle style;
  final TextAlign? textAlign;

  @override
  Widget build(BuildContext context) => Semantics(
    header: true,
    child: Text(text, style: style, textAlign: textAlign),
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
    this.leading,
    this.subtitle,
    this.additionalInfo,
    this.trailing,
    this.backgroundColor,
    this.onTap,
    super.key,
  });

  final Widget title;
  final Widget? leading;
  final Widget? subtitle;
  final Widget? additionalInfo;
  final Widget? trailing;
  final Color? backgroundColor;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final tile = CupertinoListTile(
      padding: const EdgeInsetsDirectional.fromSTEB(_tileTextInset, 14, 14, 14),
      backgroundColor: backgroundColor,
      leading: leading,
      title: title,
      subtitle: subtitle,
      additionalInfo: additionalInfo,
      trailing: trailing == null
          ? null
          : Padding(
              padding: const EdgeInsetsDirectional.only(start: 16),
              child: trailing,
            ),
      onTap: onTap,
    );
    return onTap == null
        ? tile
        : SelectionContainer.disabled(
            child: MouseRegion(cursor: SystemMouseCursors.click, child: tile),
          );
  }
}

/// An icon drawn as a glyph of the text next to it, so it shares the text's
/// baseline and line height in a row aligned on [TextBaseline.alphabetic].
/// It is decorative, so screen readers skip it.
class TextIcon extends StatelessWidget {
  const TextIcon(this.icon, {this.style, this.color, super.key});

  final IconData icon;
  final TextStyle? style;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final textStyle = DefaultTextStyle.of(context).style.merge(style);
    return ExcludeSemantics(
      child: Text(
        String.fromCharCode(icon.codePoint),
        style: TextStyle(
          inherit: false,
          color: color ?? textStyle.color,
          fontSize: textStyle.fontSize,
          fontFamily: icon.fontFamily,
          package: icon.fontPackage,
        ),
        strutStyle: StrutStyle.fromTextStyle(textStyle, forceStrutHeight: true),
      ),
    );
  }
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
            Padding(
              padding: EdgeInsets.symmetric(horizontal: appInputSpacing / 2),
              child: Icon(
                CupertinoIcons.chevron_right,
                size: 16,
                color: AppColors.of(context).secondaryText,
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
              child: SelectionContainer.disabled(
                child: Text(crumb.label, style: crumb.style),
              ),
            ),
        ],
      ],
    );
  }
}

/// A page's actions below its title. While [pinned], the row stays at the top
/// of the page as it scrolls, with its actions at either end, so that Save is
/// always within reach.
class PageActionBar extends StatelessWidget {
  const PageActionBar({
    required this.pinned,
    required this.children,
    super.key,
  });

  final bool pinned;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: pageMargin(context).left,
        vertical: appInputSpacing,
      ),
      decoration: BoxDecoration(
        color: CupertinoTheme.of(context).scaffoldBackgroundColor,
        border: pinned
            ? Border(
                bottom: BorderSide(
                  color: AppColors.of(context).separator,
                  width: 0,
                ),
              )
            : null,
      ),
      child: pinned
          ? Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: children,
            )
          : Wrap(
              spacing: appInputSpacing,
              runSpacing: appInputSpacing,
              children: children,
            ),
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
/// [actions] go from leading to trailing; more than two stack with the
/// trailing one on top, following the iOS alert layout.
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
          child: Container(
            clipBehavior: Clip.antiAlias,
            decoration: BoxDecoration(
              color: AppColors.of(context).surface,
              borderRadius: BorderRadius.circular(appRadius),
            ),
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
                      child: actions.length > 2
                          ? Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              spacing: appInputSpacing / 2,
                              children: actions.reversed.toList(),
                            )
                          : Wrap(
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
