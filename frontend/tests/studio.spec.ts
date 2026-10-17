import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    let status = 'ready';
    const state = () => ({status, completed: 0, total: 3, matches: 0, elapsed: 0, rows: [], logs: [], error: '', output: false, update: {status: 'current', message: 'Bạn đang dùng bản mới nhất.', progress: 0}});
    window.pywebview = {api: Object.fromEntries(Object.entries({
      get_bootstrap: () => ({version: '1.0.2', build: 'ui-test', has_api_key: true}),
      get_state: state,
      save_preferences: () => true,
      check_updates: () => true,
      start_scan: () => {status = 'running'; return true;},
      stop_scan: () => {status = 'stopped'; return true;},
      open_workbook: () => ({filename: 'keywords.xlsx', sheets: ['Topics']}),
      workbook_page: (_sheet: unknown, query: unknown) => ({columns: ['Keyword'], rows: query ? [['alpha']] : [['alpha'], ['beta']], page: 0, pages: 1, total: query ? 1 : 2, original_total: 2}),
      import_keywords: () => ['alpha', 'beta'],
    }).map(([name, method]) => [name, async (...args: unknown[]) => ({ok: true, data: method(...args as [])})]))};
  });
  await page.goto('/');
  await expect(page.getByText('Xử lý trên máy', {exact: true})).toBeVisible();
});

test('theme, scan lifecycle and responsive layout', async ({page}) => {
  await page.screenshot({path: '../artifacts/ui/react-dark.png', fullPage: true});
  await page.getByRole('button', {name: 'Chuyển giao diện sáng'}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.screenshot({path: '../artifacts/ui/react-light.png', fullPage: true});
  await page.getByRole('button', {name: /Bắt đầu khám phá/}).click();
  await expect(page.getByRole('button', {name: 'Dừng', exact: true})).toBeEnabled();
  await page.getByRole('button', {name: 'Dừng', exact: true}).click();
  await expect(page.getByRole('button', {name: /Bắt đầu khám phá/})).toBeEnabled();
  await page.setViewportSize({width: 800, height: 600});
  await expect(page.getByRole('button', {name: 'Mở menu và bộ lọc'})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.locator('.sidebar')).toHaveCSS('visibility', 'hidden');
  await page.screenshot({path: '../artifacts/ui/react-compact.png', fullPage: true, animations: 'disabled'});
  await page.getByRole('button', {name: 'Mở menu và bộ lọc'}).click();
  await expect(page.getByLabel('YouTube API Key', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Đóng menu', exact: true}).click();
  await expect(page.locator('.sidebar')).toHaveCSS('visibility', 'hidden');
});

test('Excel search and confirmed import use the original column', async ({page}) => {
  await page.getByRole('button', {name: 'Nhập Excel', exact: true}).click();
  await expect(page.getByRole('cell', {name: 'beta', exact: true})).toBeVisible();
  await page.getByRole('textbox', {name: 'Tìm trong bảng'}).fill('alpha');
  await expect(page.getByRole('cell', {name: 'beta', exact: true})).toHaveCount(0);
  await page.getByRole('button', {name: 'Nhập cột từ khóa'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', {name: 'Xác nhận', exact: true}).click();
  await expect(page.getByRole('textbox', {name: 'Danh sách từ khóa'})).toHaveValue('alpha\nbeta');
});
