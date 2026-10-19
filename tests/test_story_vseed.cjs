// Regress local theme merging and Skill assembly with the pinned VSeed UMD.
// VSeed's own chart/annotation/coordinate behavior belongs in its library tests.
// npm ci --prefix evals && node --test tests/test_story_vseed.cjs
const assert = require('node:assert/strict');
const { test } = require('node:test');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const vm = require('node:vm');
// Load the browser UMD contract independent of the npm package's ESM metadata.
const bundle = {exports: {}};
const filename = path.resolve(__dirname, '../evals/node_modules/@visactor/vseed/dist/umd/index.js');
vm.runInThisContext('(function(module,exports){' + fs.readFileSync(filename, 'utf8') + '\n})', {filename})(bundle, bundle.exports);
const runtime = bundle.exports;
runtime.registerAll();

// Exercise the private merge helper in a fresh realm for each test so a
// regression cannot pollute this test runner or another test's prototypes.
const storySource = fs.readFileSync(path.resolve(__dirname, '../skills/data-storytelling/scripts/vseed-render.js'), 'utf8');
const helpersStart = storySource.indexOf('  function isPlainObject(value)');
const helpersEnd = storySource.indexOf('  function getThemeChartConfig(', helpersStart);
assert.ok(helpersStart >= 0 && helpersEnd > helpersStart, 'Story theme helpers must be available');
const themeHelpers = storySource.slice(helpersStart, helpersEnd);
function mergeResult(code) {
  return JSON.parse(vm.runInNewContext(themeHelpers + '\nJSON.stringify((() => {\n' + code + '\n})())'));
}

for (const key of ['__proto__', 'constructor', 'prototype']) {
  for (const nested of [false, true]) {
    test(`theme merging rejects ${key} ${nested ? 'inside nested defaults' : 'at the root'}`, () => {
      const value = key === 'constructor' ? {prototype: {polluted: true}} : {polluted: true};
      const defaults = nested ? {style: {[key]: value, radius: 4}} : {[key]: value, radius: 4};
      const result = mergeResult(`
        const target = {};
        mergeThemeDefaults(target, JSON.parse(${JSON.stringify(JSON.stringify(defaults))}));
        return {
          output: target,
          prototypeClean: !Object.prototype.hasOwnProperty.call(Object.prototype, 'polluted'),
          originalPrototype: Object.getPrototypeOf(target) === Object.prototype
        };
      `);
      assert.deepEqual(result, {
        output: nested ? {style: {radius: 4}} : {radius: 4},
        prototypeClean: true,
        originalPrototype: true,
      });
    });
  }
}

test('theme defaults preserve unrelated settings and override supported nested values', () => {
  assert.deepEqual(mergeResult(`
    const target = {barMaxWidth: 30, style: {color: 'blue', radius: 1}, palette: ['old']};
    const merged = mergeThemeDefaults(target, {barMaxWidth: 72, style: {radius: 4}, palette: ['new']});
    return {sameTarget: merged === target, output: merged};
  `), {
    sameTarget: true,
    output: {barMaxWidth: 72, style: {color: 'blue', radius: 4}, palette: ['new']},
  });
});

test('theme merging creates own nested settings instead of mutating inherited objects', () => {
  assert.deepEqual(mergeResult(`
    const inherited = {style: {radius: 1}};
    const target = Object.create(inherited);
    mergeThemeDefaults(target, {style: {radius: 4}});
    return {output: target, inherited, ownStyle: Object.prototype.hasOwnProperty.call(target, 'style')};
  `), {
    output: {style: {radius: 4}},
    inherited: {style: {radius: 1}},
    ownStyle: true,
  });
});

// Keep normalized axes independent of raw quantity formatting through assembly and VSeed.
const root = path.resolve(__dirname, '..');
for (const [chartType, valueAxis, categoryAxis, orient] of [
  ['columnPercent', 'yAxis', 'xAxis', 'left'],
  ['barPercent', 'xAxis', 'yAxis', 'bottom'],
]) {
  test(`${chartType} retains percent ticks after assembling raw quantity formats`, async () => {
    const spec = {
      chartType,
      dimensions: [{ id: 'period', encoding: categoryAxis }, { id: 'group', encoding: 'color' }],
      measures: [{ id: 'amount', encoding: valueAxis, numFormat: { type: 'number', suffix: ' units' } }],
    };
    const dataset = [{ period: 'A', group: 'one', amount: 25 }, { period: 'A', group: 'two', amount: 75 }];
    const assembled = JSON.parse(execFileSync('uv', ['run', '--locked', 'python', '-c', `
import json,sys
sys.path.insert(0, sys.argv[1])
from local_chart_specs import assemble_local_specs
s,d=json.load(sys.stdin)
request={"chartId":"chart","datasetRef":"data","annotations":[],"contract":{"chart_type":s["chartType"],"dimensions":s["dimensions"],"measures":s["measures"]}}
print(json.dumps(assemble_local_specs([request],{"data":d},{"chart":s})["chart"]["spec"]))
`, path.join(root, 'skills/data-storytelling/scripts')], { cwd: root, input: JSON.stringify([spec, dataset]), encoding: 'utf8' }));
    const builder = runtime.Builder.from(assembled);
    await builder.prepare();
    const chart = builder.build();
    const axis = chart.axes.find(a => a.orient === orient && a.type === 'linear');
    assert.deepEqual([0, 0.5, 1].map(value => axis.label.formatMethod(value)), ['0.00%', '50.00%', '100.00%']);
    assert.deepEqual(assembled.dataset, dataset);
    assert.equal(assembled.measures[0].numFormat.suffix, ' units');
  });
}
