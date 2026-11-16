// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/form/field_def.dart';
import 'package:heritrace/form/form_model.dart';
import 'package:heritrace/form/validator.dart';

import '../helpers.dart';
import 'fixtures.dart';

const messages = ValidationMessages(
  required: 'required',
  invalidUrl: 'invalid url',
  invalidIri: 'invalid iri',
  exceeds: _exceeds,
  invalidInput: _invalidInput,
  tooMany: _tooMany,
  tooFew: _tooFew,
  atLeast: _atLeast,
  atMost: _atMost,
  greaterThan: _greaterThan,
  lessThan: _lessThan,
);

String _atLeast(num limit) => 'at least $limit';

String _atMost(num limit) => 'at most $limit';

String _greaterThan(num limit) => 'greater than $limit';

String _lessThan(num limit) => 'less than $limit';

String _invalidInput(String expected) => 'expected $expected';

String _tooMany(String name, int count, int max) =>
    '$name too many $count/$max';

String _tooFew(String name, int count, int min) => '$name too few $count/$min';

void main() {
  late EntityNode root;

  setUp(() {
    root = EntityNode(
      entityType: article,
      entityShape: articleShape,
      fields: articleFields(),
      depth: 0,
    );
  });

  tearDown(() => root.dispose());

  FieldGroup group(EntityNode node, String uri) =>
      node.groups.firstWhere((g) => g.def.uri == uri);

  EntityNode linkNode({required int min}) => EntityNode(
    entityType: article,
    entityShape: articleShape,
    depth: 0,
    fields: parseFormFields([
      [
        documentContext,
        [
          {
            'uri': documentContext,
            'displayName': 'Volume',
            'editor': shuiAutoCompleteEditor,
            'entityType': article,
            'subjectShape': articleShape,
            'nodeShape': volumeShape,
            'objectClass': volume,
            'min': min,
            'nestedShape': [
              {
                'uri': sequenceIdentifier,
                'displayName': 'Number',
                'editor': textFieldEditor,
                'entityType': volume,
                'subjectShape': volumeShape,
                'datatypes': [xsdString],
                'min': 1,
                'max': 1,
              },
            ],
          },
        ],
      ],
    ]),
  );

  test('an empty optional link is not validated', () {
    final node = linkNode(min: 0);
    addTearDown(node.dispose);
    group(node, documentContext).addItem();

    expect(
      validateEntity(
        node,
        messages,
        path: ['Article'],
        values: nodeValues(node),
      ),
      isEmpty,
    );
  });

  test('an empty required link reports the link itself', () {
    final node = linkNode(min: 1);
    addTearDown(node.dispose);

    final errors = validateEntity(
      node,
      messages,
      path: ['Article'],
      values: nodeValues(node),
    );

    expect(errors.map((e) => e.fullMessage), ['Volume: required']);
    expect(errors.single.item, group(node, documentContext).items.single);
  });

  test('required empty fields are reported with their path', () {
    final errors = validateEntity(
      root,
      messages,
      path: ['Journal Article'],
      values: nodeValues(root),
    );

    expect(errors.map((e) => e.fullMessage), ['Title: required']);
    expect(errors.single.path, ['Journal Article']);
    expect(errors.single.required, isTrue);
    expect(errors.single.item, group(root, title).items.single);
  });

  test('datatype problems use the format of the selected date type', () {
    (group(root, title).items.single as LiteralItem).setValue('Ok');
    final date = group(root, pubDate).addItem() as DateItem;
    date.setValue('2023-13-01');

    expect(
      validateEntity(
        root,
        messages,
        path: ['Journal Article'],
        values: nodeValues(root),
      ).map((e) => e.fullMessage),
      ['Publication Date: expected date in format YYYY-MM-DD'],
    );

    date.setDateType(DateType.year);
    date.setValue('23');
    expect(
      validateEntity(
        root,
        messages,
        path: ['Journal Article'],
        values: nodeValues(root),
      ).map((e) => e.fullMessage),
      ['Publication Date: expected year in format YYYY'],
    );
  });

  test('nested entities are validated under their own path', () {
    (group(root, title).items.single as LiteralItem).setValue('Ok');
    final role = group(root, documentContext).addItem() as NestedItem;
    final authorItem = heldByItem(role);
    (group(authorItem.child, name).addItem() as LiteralItem).setValue('Jane');
    group(authorItem.child, identifier).addItem();

    final errors = validateEntity(
      root,
      messages,
      path: ['Journal Article'],
      values: nodeValues(root),
    );

    expect(errors.single.fullMessage, 'Value: required');
    expect(errors.single.path, [
      'Journal Article',
      'Author',
      'Held By',
      'Identifier',
    ]);
  });

  test('cardinality counts only user added items against the maximum', () {
    (group(root, title).items.single as LiteralItem).setValue('Ok');
    final titles = group(root, title);
    titles.addItem();
    (titles.items.last as LiteralItem).setValue('Second');

    expect(
      validateEntity(
        root,
        messages,
        path: ['Journal Article'],
        values: nodeValues(root),
      ).map((e) => e.fullMessage),
      ['Title too many 2/1'],
    );
  });

  List<String> Function(String) boundMessages(Map<String, num> bounds) {
    const count = 'http://example.org/count';
    final node = EntityNode(
      entityType: article,
      entityShape: articleShape,
      depth: 0,
      fields: parseFormFields([
        [
          count,
          [
            {
              'uri': count,
              'displayName': 'Count',
              'editor': shuiNumberFieldEditor,
              'entityType': article,
              'subjectShape': articleShape,
              'datatypes': ['http://www.w3.org/2001/XMLSchema#integer'],
              'min': 1,
              'max': 1,
              ...bounds,
            },
          ],
        ],
      ]),
    );
    addTearDown(node.dispose);
    final item = group(node, count).items.single as LiteralItem;
    return (value) {
      item.setValue(value);
      return validateEntity(
        node,
        messages,
        path: ['Article'],
        values: nodeValues(node),
      ).map((e) => e.fullMessage).toList();
    };
  }

  test('numeric values outside the inclusive bounds are reported', () {
    final messagesFor = boundMessages({'minInclusive': 0, 'maxInclusive': 10});

    expect(messagesFor('-1'), ['Count: at least 0']);
    expect(messagesFor('11'), ['Count: at most 10']);
    expect(messagesFor('10'), isEmpty);
    expect(messagesFor('x'), ['Count: expected whole number']);
  });

  test('numeric values outside the exclusive bounds are reported', () {
    final messagesFor = boundMessages({'minExclusive': 0, 'maxExclusive': 10});

    expect(messagesFor('0'), ['Count: greater than 0']);
    expect(messagesFor('10'), ['Count: less than 10']);
    expect(messagesFor('9'), isEmpty);
  });

  test('datatype rules accept and reject representative values', () {
    const xsd = 'http://www.w3.org/2001/XMLSchema#';
    expect(datatypeProblem('42', ['${xsd}integer']), isNull);
    expect(datatypeProblem('4.2', ['${xsd}integer']), 'whole number');
    expect(datatypeProblem('4.2', ['${xsd}integer', '${xsd}decimal']), isNull);
    expect(
      datatypeProblem('300', ['${xsd}unsignedByte']),
      'whole number between 0 and 255',
    );
    expect(
      datatypeProblem('2023-02-30', ['${xsd}date']),
      'date in format YYYY-MM-DD',
    );
    expect(datatypeProblem('9223372036854775807', ['${xsd}long']), isNull);
    expect(
      datatypeProblem('9223372036854775808', ['${xsd}long']),
      'whole number between -9223372036854775808 and 9223372036854775807',
    );
    expect(
      datatypeProblem('18446744073709551615', ['${xsd}unsignedLong']),
      isNull,
    );
    expect(datatypeProblem('2023-12', ['${xsd}gYearMonth']), isNull);
    expect(datatypeProblem('P1Y2M', ['${xsd}yearMonthDuration']), isNull);
    expect(datatypeProblem('anything', [xsdString]), isNull);
    expect(datatypeProblem('anything', ['http://example.org/unknown']), isNull);
  });

  test('an empty inline value leaves an optional nested entity out', () {
    (group(root, title).items.single as LiteralItem).setValue('Ok');
    group(root, documentContext).addItem();

    expect(
      validateEntity(
        root,
        messages,
        path: ['Journal Article'],
        values: nodeValues(root),
      ),
      isEmpty,
    );
  });

  test('hasAnyValue ignores mandatory values', () {
    expect(hasAnyValue(root), isFalse);
    (group(root, title).items.single as LiteralItem).setValue('Ok');
    expect(hasAnyValue(root), isTrue);
  });

  test('hasAnyValue ignores empty nested entities', () {
    final role = group(root, documentContext).addItem() as NestedItem;
    final authorItem = heldByItem(role);
    expect(hasAnyValue(root), isFalse);

    authorItem.selectExisting('https://w3id.org/oc/meta/ar/1', 'An author');
    expect(hasAnyValue(root), isTrue);
  });

  test("a value matches its field's patterns and one that applies", () {
    const scheme = 'http://example.org/scheme';
    const code = 'http://example.org/code';
    const field = <String, Object?>{
      'uri': code,
      'displayName': 'Code',
      'editor': textFieldEditor,
      'entityType': article,
      'subjectShape': articleShape,
      'patterns': [
        {'condition': null, 'pattern': r'^\S+$', 'message': null},
        {
          'condition': {'path': scheme, 'value': 'doi'},
          'pattern': r'^10\.',
          'message': 'not a DOI',
        },
        {
          'condition': {'path': scheme, 'value': 'doi'},
          'pattern': r'^doi:',
          'message': 'not a prefixed DOI',
        },
      ],
    };
    final def = parseFormFields([
      [
        code,
        [field],
      ],
    ]).single;
    List<String> problems(String value, List<String> schemes) => valueProblems(
      value,
      def,
      const [],
      messages,
      (predicate) => predicate == scheme ? schemes : const [],
    );

    expect(problems('a b', const []), [r'expected ^\S+$']);
    expect(problems('x', const []), isEmpty);
    expect(problems('x', const ['doi']), ['not a DOI']);
    expect(problems('doi:10.1/x', const ['doi']), isEmpty);
  });

  test('a field of IRIs takes any IRI and nothing else', () {
    const source = 'http://example.org/source';
    final def = parseFormFields([
      [
        source,
        [
          {
            'uri': source,
            'displayName': 'Source',
            'editor': iriEditor,
            'entityType': article,
            'subjectShape': articleShape,
            'nodeKind': shIri,
          },
        ],
      ],
    ]).single;
    List<String> problems(String value) =>
        valueProblems(value, def, const [], messages, (_) => const []);

    expect(problems('urn:isbn:0451450523'), isEmpty);
    expect(problems('not an iri'), ['invalid iri']);
  });

  test('a value does not exceed the values of the field it names', () {
    const start = 'http://example.org/start';
    const end = 'http://example.org/end';
    final def = parseFormFields([
      [
        start,
        [
          {
            'uri': start,
            'displayName': 'Start',
            'editor': textFieldEditor,
            'entityType': article,
            'subjectShape': articleShape,
            'lessThanOrEquals': [
              {'path': end, 'name': 'End'},
            ],
          },
        ],
      ],
    ]).single;
    List<String> problems(String value, List<String> ends) =>
        valueProblems(value, def, const [], messages, (_) => ends);

    expect(problems('2', const ['10']), isEmpty);
    expect(problems('2020-05', const ['2020-04']), ['exceeds End']);
    expect(problems('2020-05-01', const ['2020-05-01', '2021-01-01']), isEmpty);
    expect(problems('2020', const ['2020-05-01']), ['exceeds End']);
    expect(problems('2', const []), isEmpty);
  });
}

String _exceeds(String other) => 'exceeds $other';
