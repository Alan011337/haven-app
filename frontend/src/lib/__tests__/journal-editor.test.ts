import test from 'node:test';
import assert from 'node:assert/strict';
import {
  insertCodeBlock,
  insertLink,
  insertMarkdownImage,
  prefixLines,
  prefixNumberedLines,
  wrapSelection,
} from '../journal-editor.ts';

test('wrapSelection wraps selected text with markdown markers', () => {
  const result = wrapSelection('hello world', { start: 6, end: 11 }, '**', '**', '重點');
  assert.equal(result.value, 'hello **world**');
  assert.deepEqual(result.selection, { start: 8, end: 13 });
});

test('prefixLines adds markdown prefixes to all selected lines', () => {
  const result = prefixLines('first\nsecond', { start: 0, end: 12 }, '> ', '引用');
  assert.equal(result.value, '> first\n> second');
});

test('prefixNumberedLines numbers each selected line', () => {
  const result = prefixNumberedLines('alpha\nbeta', { start: 0, end: 10 }, '項目');
  assert.equal(result.value, '1. alpha\n2. beta');
});

test('insertCodeBlock inserts fenced block around placeholder when nothing is selected', () => {
  const result = insertCodeBlock('note', { start: 4, end: 4 }, 'console.log()');
  assert.equal(result.value, 'note```\nconsole.log()\n```');
});

test('insertLink inserts markdown link and selects the URL segment', () => {
  const result = insertLink('read this', { start: 0, end: 4 }, '連結文字', 'https://haven.app');
  assert.equal(result.value, '[read](https://haven.app) this');
  assert.deepEqual(result.selection, { start: 7, end: 24 });
});

test('insertMarkdownImage inserts a markdown image snippet', () => {
  const result = insertMarkdownImage('', { start: 0, end: 0 }, 'Sunrise', 'attachment:123');
  assert.equal(result.value, '![Sunrise](attachment:123)');
});

test('insertMarkdownImage preserves block spacing around existing content', () => {
  const result = insertMarkdownImage(
    '## Heading',
    { start: 0, end: 0 },
    'Sunrise',
    'attachment:123',
  );
  assert.equal(result.value, '![Sunrise](attachment:123)\n\n## Heading');
});
