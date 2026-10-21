import {expect, test} from '@playwright/test';

test('saved scan shows reset countdown and resumes with the selected budget', async ({page}) => {
  await page.addInitScript(() => {
    let resumed: unknown = null;
    const methods: Record<string, (...args: any[]) => unknown> = {
      get_bootstrap: () => ({version: '1.0.2', has_api_key: true, keywords: 'AI'}),
      get_state: () => ({status: 'stopped', completed: 1, total: 2, matches: 0,
        elapsed: 0, rows: [], logs: [], error: '', output: true, search_used: 5,
        search_budget: 5, can_resume: true, resume_available: true,
        resume_keyword: 'Make.com', reset_seconds: 3661,
        update: {status: 'current', message: '', progress: 0}}),
      save_preferences: () => true, set_language: () => true, set_keywords_dirty: () => true,
      resume_scan: (settings: unknown) => {resumed = settings; return true;},
      test_resumed: () => resumed,
    };
    window.pywebview = {api: Object.fromEntries(Object.entries(methods).map(([name, fn]) =>
      [name, async (...args: unknown[]) => ({ok: true, data: fn(...args)})]))};
  });
  await page.goto('/');
  await expect(page.getByText('Quota resets in', {exact: false})).toContainText('01:01:01');
  await expect(page.getByText('Saved keyword', {exact: false})).toContainText('Make.com');
  await page.locator('#search-budget').fill('12');
  await page.getByRole('button', {name: 'Resume saved scan'}).click();
  await expect.poll(() => page.evaluate(async () =>
    (await window.pywebview!.api.test_resumed()).data)).toEqual({api_key: '', search_budget: '12'});
});
