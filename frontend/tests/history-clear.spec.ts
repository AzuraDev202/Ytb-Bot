import {expect, test} from '@playwright/test';

test('clearing history requires confirmation and refreshes the empty view', async ({page}) => {
  await page.addInitScript(() => {
    let cleared = false;
    const methods: Record<string, (...args: any[]) => unknown> = {
      get_bootstrap: () => ({version: '1.0.2', has_api_key: true, keywords: 'AI'}),
      get_state: () => ({status: 'ready', completed: 0, total: 0, matches: 0,
        elapsed: 0, rows: [], logs: [], error: '', output: false,
        update: {status: 'current', message: '', progress: 0}}),
      list_results: () => cleared ? [] : [{id: 1, created: '2026-10-21', status: 'complete', count: 0, error: ''}],
      open_results: () => ({path: 'history', sheets: ['Scan #1'], kind: 'results'}),
      results_page: () => ({columns: [], rows: [], total: 0, page: 0, pages: 1}),
      contact_groups: () => [], list_bulk_mail: () => [],
      save_preferences: () => true, set_keywords_dirty: () => true,
      clear_scan_history: () => {cleared = true; return true;},
      test_cleared: () => cleared,
    };
    window.pywebview = {api: Object.fromEntries(Object.entries(methods).map(([name, fn]) =>
      [name, async (...args: unknown[]) => ({ok: true, data: fn(...args)})]))};
  });
  await page.goto('/');
  await page.getByRole('button', {name: /View results in the bot/}).click();
  const clear = page.getByRole('button', {name: 'Clear scan history', exact: true});
  await expect(clear).toBeEnabled();
  await clear.click();
  await expect(page.getByRole('dialog')).toContainText('Previously found channels may appear again.');
  await page.getByRole('button', {name: 'Cancel', exact: true}).click();
  expect(await page.evaluate(async () => (await window.pywebview!.api.test_cleared()).data)).toBe(false);
  await clear.click();
  await page.getByRole('button', {name: 'Confirm', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'No discovery scans yet'})).toBeVisible();
  await expect(clear).toBeDisabled();
});
