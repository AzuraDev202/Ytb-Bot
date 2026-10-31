import {expect, test} from '@playwright/test';

test.beforeEach(async ({page}) => {
  await page.addInitScript(() => {
    const channels = [{id: 'one', name: 'Creator One'}, {id: 'two', name: 'Creator Two'}];
    type Batch = {id: string; status: string; sender: string; account_id: string; subject: string; body: string; created: string; recipients: {email: string; channels: typeof channels; status: string}[]};
    let batch: Batch | null = null;
    let failStart = false;
    const records: string[] = [];
    const methods: Record<string, (...args: any[]) => unknown> = {
      get_bootstrap: () => ({version: '1.0.2', build: 'bulk-test', has_api_key: true, keywords: 'AI'}),
      get_state: () => ({status: 'ready', completed: 0, total: 0, matches: 0, elapsed: 0, rows: [], logs: [], error: '', output: false, update: {status: 'current', message: '', progress: 0}}),
      save_preferences: () => true, set_language: () => true, set_keywords_dirty: () => true,
      list_results: () => [], set_bulk_dirty: () => true,
      contact_groups: () => [{id: 'shared', kind: 'email', value: 'shared@example.com', channels, last_status: '', last_created: ''}, {id: 'social', kind: 'social', value: 'https://facebook.com/creator', channels, last_status: '', last_created: ''}],
      get_mail_state: () => ({configured: true, connecting: false, error: '', accounts: [{id: 'sender', email: 'me@example.com'}]}),
      list_bulk_mail: () => batch ? [batch] : [], get_bulk_mail: () => batch,
      prepare_bulk_mail: (payload: {subject: string; body: string}) => {batch = {id: 'batch', status: 'draft', sender: 'me@example.com', account_id: 'sender', subject: payload.subject, body: payload.body, created: '2026-10-18T00:00:00Z', recipients: [{email: 'shared@example.com', channels, status: 'pending'}]}; return batch;},
      start_bulk_mail: () => {if (!batch) throw new Error('missing'); batch.status = failStart ? 'interrupted' : 'running'; batch.recipients[0].status = failStart ? 'unknown' : 'sending'; if (failStart) throw new Error('Connection lost after request'); return batch;},
      stop_bulk_mail: () => {if (!batch) throw new Error('missing'); batch.status = 'stopped'; batch.recipients[0].status = 'unknown'; return batch;},
      test_calls: () => records,
      test_fail_start: () => {failStart = true; return true;},
    };
    window.pywebview = {api: Object.fromEntries(Object.entries(methods).map(([name, method]) => [name, async (...args: unknown[]) => {records.push(name); try {return {ok: true, data: method(...args)};} catch (reason) {return {ok: false, error: String(reason)};}}]))};
  });
  await page.goto('/');
  await page.getByRole('button', {name: /View results in the bot/}).click();
  await page.getByRole('button', {name: 'Grouped contacts', exact: true}).click();
});

test('contact filtering preserves selection and supports clear and reset actions', async ({page}) => {
  await expect(page.getByText('Your reviewed batches and send results will appear here.')).toBeVisible();
  await page.locator('.contact-group-label', {hasText: 'shared@example.com'}).click();
  await expect(page.getByRole('checkbox', {name: 'shared@example.com'})).toBeChecked();
  await page.getByRole('textbox', {name: 'Search contacts'}).fill('missing address');
  await expect(page.getByRole('heading', {name: 'No matching contacts'})).toBeVisible();
  await expect(page.locator('.contact-selection-bar [role=status]')).toContainText('1 selected');
  await page.getByRole('button', {name: 'Reset filters'}).click();
  await expect(page.getByRole('checkbox', {name: 'shared@example.com'})).toBeChecked();
  await page.getByRole('button', {name: 'Clear selection'}).click();
  await expect(page.getByRole('checkbox', {name: 'shared@example.com'})).not.toBeChecked();
  await expect(page.getByRole('button', {name: /Compose bulk email/})).toBeDisabled();
});

test('remove failed email selection confirms and keeps uncertain contacts', async ({page}) => {
  await page.evaluate(() => {
    let removed = false;
    window.pywebview!.api.contact_groups = async () => ({ok: true, data: [
      ...(!removed ? [{id: 'failed', kind: 'email', value: 'failed@example.com', channels: [{id: 'a', name: 'Failed Creator'}], last_status: 'failed', last_created: ''}] : []),
      {id: 'uncertain', kind: 'email', value: 'unknown@example.com', channels: [{id: 'b', name: 'Unknown Creator'}], last_status: 'unknown', last_created: ''},
    ]});
    window.pywebview!.api.remove_failed_contacts = async (...args: unknown[]) => {
      if (JSON.stringify(args[0]) !== JSON.stringify(['failed'])) throw new Error('Unexpected removal');
      removed = true; return {ok: true, data: 1};
    };
  });
  await page.getByRole('button', {name: 'Refresh contacts', exact: true}).click();
  await page.getByRole('checkbox', {name: 'failed@example.com', exact: true}).check();
  await page.getByRole('checkbox', {name: 'unknown@example.com', exact: true}).check();
  await page.getByRole('button', {name: 'Remove selected failed emails', exact: true}).click();
  await expect(page.getByRole('dialog')).toContainText('Remove 1 rejected email addresses');
  await page.getByRole('button', {name: 'Cancel', exact: true}).click();
  await expect(page.getByRole('checkbox', {name: 'failed@example.com', exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Remove selected failed emails', exact: true}).click();
  await page.getByRole('button', {name: 'Confirm', exact: true}).click();
  await expect(page.getByRole('checkbox', {name: 'failed@example.com', exact: true})).toHaveCount(0);
  await expect(page.getByRole('checkbox', {name: 'unknown@example.com', exact: true})).toBeVisible();
});

test('contact controls remain reachable on a narrow light workspace', async ({page}) => {
  await page.setViewportSize({width: 375, height: 812});
  await page.getByRole('button', {name: 'Switch to light theme'}).click();
  const filter = page.getByRole('textbox', {name: 'Search contacts'});
  expect((await filter.boundingBox())!.height).toBeGreaterThanOrEqual(40);
  await page.getByRole('checkbox', {name: 'shared@example.com'}).focus();
  await page.keyboard.press('Space');
  await expect(page.getByRole('checkbox', {name: 'shared@example.com'})).toBeChecked();
  const width = await page.evaluate(() => ({client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth}));
  expect(width.scroll).toBeLessThanOrEqual(width.client);
  await expect(page.getByRole('button', {name: /Compose bulk email/})).toBeEnabled();
});

test('shared address has one selection, explicit preview/start, stop and uncertain history', async ({page}) => {
  await expect(page.getByRole('checkbox', {name: 'shared@example.com'})).toHaveCount(1);
  await expect(page.locator('.contact-group-list')).toContainText('Creator One, Creator Two');
  await page.getByRole('checkbox', {name: 'shared@example.com'}).check();
  await page.getByRole('button', {name: /Compose bulk email/}).click();
  await page.getByRole('textbox', {name: 'Email subject'}).fill('Proposal');
  await page.getByRole('textbox', {name: 'Contact message'}).fill('Hello creators');
  await page.getByRole('button', {name: 'Preview batch'}).click();
  await expect(page.locator('.bulk-recipients li')).toHaveCount(1);
  const calls = await page.evaluate(async () => (await window.pywebview!.api.test_calls()).data as string[]);
  expect(calls.filter(method => method === 'start_bulk_mail')).toHaveLength(0);
  await page.getByRole('button', {name: 'Send batch', exact: true}).click();
  await page.getByRole('button', {name: 'Stop batch', exact: true}).click();
  await expect(page.getByRole('dialog')).toContainText('Outcome uncertain');
  await expect(page.getByRole('button', {name: 'Send batch', exact: true})).toHaveCount(0);
  await page.getByRole('button', {name: 'Close composer', exact: true}).click();
  await page.locator('.bulk-history button').click();
  await expect(page.getByRole('dialog')).toContainText('Check Sent in Gmail');
  await expect(page.getByRole('button', {name: 'Send batch', exact: true})).toHaveCount(0);
});

test('language switches and refresh keep open draft; save close persists review', async ({page}) => {
  await page.setViewportSize({width: 375, height: 812});
  await page.getByRole('checkbox', {name: 'shared@example.com'}).check();
  await page.getByRole('button', {name: /Compose bulk email/}).click();
  await page.getByRole('textbox', {name: 'Email subject'}).fill('Keep subject');
  await page.getByRole('textbox', {name: 'Contact message'}).fill('Keep my draft');
  await page.getByRole('dialog').getByRole('combobox', {name: 'Language', exact: true}).selectOption('vi');
  await expect(page.locator('.bulk-composer textarea')).toHaveValue('Keep my draft');
  await page.getByRole('dialog').locator('.language-picker select').selectOption('en');
  await page.keyboard.press('Escape');
  await page.getByRole('button', {name: 'Save and close', exact: true}).click();
  await page.locator('.bulk-history button').click();
  await expect(page.getByRole('dialog')).toContainText('Keep my draft');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('lost start reply recovers persisted uncertain status without enabling retry', async ({page}) => {
  await page.evaluate(async () => {await window.pywebview!.api.test_fail_start();});
  await page.getByRole('checkbox', {name: 'shared@example.com'}).check();
  await page.getByRole('button', {name: /Compose bulk email/}).click();
  await page.getByRole('textbox', {name: 'Email subject'}).fill('Proposal');
  await page.getByRole('textbox', {name: 'Contact message'}).fill('Hello');
  await page.getByRole('button', {name: 'Preview batch'}).click();
  await page.getByRole('button', {name: 'Send batch', exact: true}).click();
  await expect(page.getByRole('dialog')).toContainText('Outcome uncertain');
  await expect(page.getByRole('button', {name: 'Send batch', exact: true})).toHaveCount(0);
  await page.getByRole('button', {name: 'Close composer', exact: true}).click();
  await page.locator('.bulk-history button').click();
  await expect(page.getByRole('dialog')).toContainText('Outcome uncertain');
  const calls = await page.evaluate(async () => (await window.pywebview!.api.test_calls()).data as string[]);
  expect(calls.filter(method => method === 'start_bulk_mail')).toHaveLength(1);
});
