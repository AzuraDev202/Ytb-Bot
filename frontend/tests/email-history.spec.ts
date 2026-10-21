import {expect, test} from '@playwright/test';

test('email history remains accessible without discovery scans', async ({page}) => {
  await page.addInitScript(() => {
    const methods: Record<string, (...args: any[]) => unknown> = {
      get_bootstrap: () => ({version: '1.0.2', has_api_key: true, keywords: 'AI'}),
      get_state: () => ({status: 'ready', completed: 0, total: 0, matches: 0,
        elapsed: 0, rows: [], logs: [], error: '', output: false,
        update: {status: 'current', message: '', progress: 0}}),
      list_results: () => [], contact_groups: () => [], list_bulk_mail: () => [],
      save_preferences: () => true, set_keywords_dirty: () => true,
      email_contact_history: () => [{id: 'mail', channel_id: 'UC-creator', name: 'Sent Creator',
        recipient: 'creator@example.com', created: '2026-10-21T00:00:00Z', status: 'accepted'}],
    };
    window.pywebview = {api: Object.fromEntries(Object.entries(methods).map(([name, fn]) =>
      [name, async (...args: unknown[]) => ({ok: true, data: fn(...args)})]))};
  });
  await page.goto('/');
  await page.getByRole('button', {name: /View results in the bot/}).click();
  await expect(page.getByRole('heading', {name: 'No discovery scans yet'})).toBeVisible();
  await page.getByRole('button', {name: 'Email contact history', exact: true}).click();
  await expect(page.getByRole('cell', {name: 'Sent Creator', exact: true})).toBeVisible();
  await expect(page.getByRole('cell', {name: 'Gmail accepted the request', exact: true})).toBeVisible();
  await page.getByRole('textbox', {name: 'Search email history'}).fill('missing');
  await expect(page.getByText('No email history found.')).toBeVisible();
});
