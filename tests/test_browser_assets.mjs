import assert from 'node:assert/strict';
import path from 'node:path';
import { test } from 'node:test';
import { assetPath } from '../evals/scripts/local-browser-assets.mjs';

const modules = path.resolve('node_modules');
const versions = { '@visactor/vchart': '2.1.7', '@visactor/vtable': '1.26.8' };

test('maps pinned Story chart and table bundles to local files', () => {
  assert.equal(
    assetPath('https://unpkg.com/@visactor/vchart@2.1.7/build/index.min.js', modules, versions),
    path.join(modules, '@visactor/vchart/build/index.min.js')
  );
  assert.equal(
    assetPath('https://unpkg.com/@visactor/vtable@1.26.8/dist/vtable.min.js', modules, versions),
    path.join(modules, '@visactor/vtable/dist/vtable.min.js')
  );
});

test('rejects unexpected hosts, versions and paths instead of accessing the network', () => {
  for (const url of [
    'https://example.com/index.js',
    'https://unpkg.com/@visactor/vchart@latest/build/index.min.js',
    'https://unpkg.com/@visactor/vtable@1.26.8/%2e%2e%2fsecret',
    'https://unpkg.com/@visactor/vtable@1.26.8/dist/vtable.min.js?version=other',
  ]) assert.throws(() => assetPath(url, modules, versions));
});
