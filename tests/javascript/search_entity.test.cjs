// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
// SPDX-License-Identifier: ISC

const assert = require('node:assert/strict');
const { before, after, test } = require('node:test');
const { execFileSync } = require('node:child_process');
const { readFileSync, writeFileSync, mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const vm = require('node:vm');

const context = vm.createContext({ document: {}, $: () => ({ ready() {} }) });
vm.runInContext(readFileSync('heritrace/static/js/search_entity.js', 'utf8'), context);
const template = readFileSync('heritrace/templates/top_level_search.jinja', 'utf8');
vm.runInContext(template.slice('<script>'.length, template.lastIndexOf('</script>')), context);
const image = 'adfreiburg/qlever@sha256:37d5ede193f1bffb6aebf734d15d2a4c2a3228ee102858b0c6c2e65c149a78ec';
const container = `heritrace-search-test-${process.pid}`;
const directory = mkdtempSync(join(tmpdir(), 'heritrace-search-test-'));
let endpoint;
let started = false;

before(async () => {
    const triples = [];
    for (let index = 1; index <= 7; index++) {
        triples.push(`<urn:author:${index}> a <urn:Agent>; <urn:givenName> "Arcangelo"; <urn:familyName> "Massari" .`);
    }
    triples.push(
        '<urn:other-field> a <urn:Agent>; <urn:givenName> "Marco"; <urn:familyName> "Arcangelo" .',
        '<urn:other-type> a <urn:Book>; <urn:givenName> "Arcangelo" .',
        '<urn:compound> a <urn:Agent>; <urn:givenName> "Arcangelo Michele"; <urn:familyName> "Rossi" .',
        '<urn:accent> a <urn:Agent>; <urn:givenName> "Élodie" .',
        '<urn:quote> a <urn:Agent>; <urn:givenName> "D\'Angelo" .',
        '<urn:parent> a <urn:Role>; <urn:agent> <urn:author:1> .'
    );
    writeFileSync(join(directory, 'data.ttl'), triples.join('\n'));
    execFileSync('docker', [
        'run', '--rm', '--user', `${process.getuid()}:${process.getgid()}`,
        '-v', `${directory}:/index`, '-w', '/index', '--entrypoint', 'qlever-index', image,
        '-i', 'test', '-f', 'data.ttl', '-F', 'ttl', '--add-has-word-triples',
        '-m', '256M', '--no-resource-usage-log'
    ], { stdio: 'pipe' });
    execFileSync('docker', [
        'run', '-d', '--rm', '--name', container,
        '--user', `${process.getuid()}:${process.getgid()}`,
        '-v', `${directory}:/index`, '-w', '/index', '-p', '127.0.0.1::7001',
        '--entrypoint', 'qlever-server', image, '-i', 'test', '-p', '7001',
        '-m', '512M', '--no-metrics-log', '--no-resource-usage-log'
    ], { stdio: 'pipe' });
    started = true;
    const address = execFileSync('docker', ['port', container, '7001/tcp'], { encoding: 'utf8' }).trim();
    endpoint = `http://${address}`;
    for (let attempt = 0; attempt < 100; attempt++) {
        if (execFileSync('docker', ['logs', container], { encoding: 'utf8' }).includes('The server is ready, listening for requests')) return;
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error('QLever did not become ready');
});

after(() => {
    if (started) execFileSync('docker', ['stop', container], { stdio: 'pipe' });
    rmSync(directory, { recursive: true });
});

async function entities(query) {
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: { Accept: 'application/sparql-results+json' },
        body: new URLSearchParams({ query })
    });
    const result = await response.json();
    assert.equal(response.status, 200, JSON.stringify(result));
    return result.results.bindings.map(binding => binding.entity.value);
}

function search(term, offset = 0, enabled = true) {
    return context.generateSearchQuery(term, 'urn:Agent', 'urn:givenName', 'qlever', enabled, null, offset);
}

test('indexed autocomplete filters the field and type and paginates distinct entities', async () => {
    assert.deepEqual(await entities(search('ARCANG')), [
        'urn:author:1', 'urn:author:2', 'urn:author:3', 'urn:author:4', 'urn:author:5'
    ]);
    assert.deepEqual(await entities(search('ARCANG', 5)), ['urn:author:6', 'urn:author:7', 'urn:compound']);
});

test('search handles multiple words, accents, apostrophes and input with no words', async () => {
    assert.deepEqual(await entities(search('Arcangelo Mich')), ['urn:compound']);
    assert.deepEqual(await entities(search('ÉLO')), ['urn:accent']);
    assert.deepEqual(await entities(search("D'Ang")), ['urn:quote']);
    assert.deepEqual(await entities(search('"\\')), []);
    assert.deepEqual(await entities(search('Missing')), []);
});

test('parent search retains constraints on the nested entity', async () => {
    const query = context.generateSearchQuery('Arcang', 'urn:Role', 'urn:givenName', 'qlever', true, 'urn:agent', 0, 'parent');
    const constrained = context.applyContextConstraints(query, {
        'urn:familyName': [{ value: 'Massari', datatypes: ['http://www.w3.org/2001/XMLSchema#string'] }]
    }, '?nestedEntity <urn:givenName> ?searchValue .');
    assert.deepEqual(await entities(constrained), ['urn:parent']);
    assert.deepEqual(await entities(constrained.replace('"Massari"', '"Rossi"')), []);
});

test('top-level suggestions use the indexed search', async () => {
    context.window = { dataset_db_triplestore: 'qlever', dataset_db_text_index_enabled: true };
    let request;
    context.$.ajax = options => { request = options; };
    context.searchSimilarTopLevelEntities('Arcangelo Mich', 'urn:Agent', 'urn:givenName', 4, () => {});
    assert.equal(request.url, '/dataset-endpoint');
    assert.deepEqual(await entities(request.data.query), ['urn:compound']);
});

test('disabled indexing retains case-insensitive substring searches', async () => {
    assert.deepEqual(await entities(search('cangelo Mich', 0, false)), ['urn:compound']);
    assert.deepEqual(await entities(search('"', 0, false)), []);
});
