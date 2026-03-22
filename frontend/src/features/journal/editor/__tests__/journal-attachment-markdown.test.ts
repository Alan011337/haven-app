import assert from 'node:assert/strict';
import test from 'node:test';
import {
  deriveJournalAttachmentAlt,
  findInsertedAttachmentIds,
  insertAttachmentMarkdown,
  preserveAttachmentMarkdown,
  stripAllAttachmentMarkdown,
  stripAttachmentMarkdown,
} from '../journal-attachment-markdown.ts';

test('deriveJournalAttachmentAlt humanizes the file name', () => {
  assert.equal(deriveJournalAttachmentAlt('window-light.png'), 'window light');
  assert.equal(deriveJournalAttachmentAlt('  .png  '), 'journal image');
});

test('findInsertedAttachmentIds returns unique attachment ids in order', () => {
  const content = [
    'intro',
    '![First](attachment:one)',
    'paragraph',
    '![Second](attachment:two)',
    '![Duplicate](attachment:one)',
  ].join('\n\n');

  assert.deepEqual(findInsertedAttachmentIds(content), ['one', 'two']);
});

test('stripAttachmentMarkdown removes the targeted image block and preserves surrounding spacing', () => {
  const content = [
    '# Title',
    '![First](attachment:one)',
    'middle paragraph',
    '![Second](attachment:two)',
    'closing thought',
  ].join('\n\n');

  assert.equal(
    stripAttachmentMarkdown(content, 'two'),
    ['# Title', '![First](attachment:one)', 'middle paragraph', 'closing thought'].join('\n\n'),
  );
});

test('stripAllAttachmentMarkdown removes every attachment block while preserving prose', () => {
  const content = [
    '![First](attachment:one)',
    '開頭段落',
    '![Second](attachment:two)',
    '結尾段落',
  ].join('\n\n');

  assert.equal(stripAllAttachmentMarkdown(content), ['開頭段落', '結尾段落'].join('\n\n'));
});

test('insertAttachmentMarkdown appends an attachment block with stable spacing', () => {
  assert.equal(
    insertAttachmentMarkdown('opening thought', {
      alt: 'window light',
      attachmentId: 'attachment-1',
    }),
    ['opening thought', '![window light](attachment:attachment-1)'].join('\n\n'),
  );
});

test('preserveAttachmentMarkdown keeps already-inserted attachments when editor export drops them', () => {
  assert.equal(
    preserveAttachmentMarkdown('opening thought\n\nclosing thought', {
      attachments: [{ file_name: 'window-light.png', id: 'attachment-1' }],
      previousContent: ['opening thought', '![window light](attachment:attachment-1)'].join('\n\n'),
    }),
    [
      'opening thought',
      'closing thought',
      '![window light](attachment:attachment-1)',
    ].join('\n\n'),
  );
});
