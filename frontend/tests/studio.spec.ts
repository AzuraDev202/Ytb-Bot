import { expect, test } from '@playwright/test';

test('edit, paste, delete and reopen the keyword table without downloading files', async ({page}) => {
  const downloads: string[] = [];
  page.on('download', download => downloads.push(download.suggestedFilename()));
  await page.getByRole('button', {name: 'Sửa bảng từ khóa', exact: true}).click();
  await page.getByRole('textbox', {name: 'Từ khóa dòng 1', exact: true}).evaluate(element => {
    const transfer = new DataTransfer(); transfer.setData('text/plain', 'New topic\tignored\nSecond topic\nThird topic');
    element.dispatchEvent(new ClipboardEvent('paste', {clipboardData: transfer, bubbles: true, cancelable: true}));
  });
  await expect(page.getByRole('textbox', {name: 'Từ khóa dòng 2', exact: true})).toHaveValue('Second topic');
  await page.getByRole('textbox', {name: 'Từ khóa dòng 2', exact: true}).fill('Edited topic');
  await page.getByRole('checkbox', {name: 'Chọn từ khóa 3', exact: true}).check();
  await page.getByRole('button', {name: 'Xóa 1', exact: true}).click();
  await page.getByRole('button', {name: 'Xác nhận', exact: true}).click();
  await page.getByRole('button', {name: 'Lưu từ khóa', exact: true}).click();
  await expect(page.getByText(/Đã lưu trong Bot ·/)).toBeVisible();
  await page.reload();
  await page.getByRole('button', {name: 'Sửa bảng từ khóa', exact: true}).click();
  await expect(page.getByRole('textbox', {name: 'Từ khóa dòng 1', exact: true})).toHaveValue('New topic');
  await expect(page.getByRole('textbox', {name: 'Từ khóa dòng 2', exact: true})).toHaveValue('Edited topic');
  await page.getByRole('button', {name: 'Thêm dòng', exact: true}).click();
  await expect(page.getByText(/Có thay đổi chưa lưu/)).toBeVisible();
  expect(downloads).toEqual([]);
  await page.screenshot({path: '../artifacts/ui/keyword-editor.png', fullPage: true});
});

test('browse result history, paginate, search and sort without downloads', async ({page}) => {
  const downloads: string[] = [];
  page.on('download', download => downloads.push(download.suggestedFilename()));
  await page.getByRole('button', {name: /Xem kết quả trong Bot/}).click();
  await expect(page.getByRole('cell', {name: 'Channel 0', exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Trang sau', exact: true}).click();
  await expect(page.getByRole('cell', {name: 'Channel 100', exact: true})).toBeVisible();
  await page.getByRole('textbox', {name: 'Tìm trong bảng'}).fill('Channel 250');
  await expect(page.getByRole('cell', {name: 'Channel 250', exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Xóa tìm kiếm'}).click();
  await page.getByRole('button', {name: 'Lượt xem', exact: true}).click();
  await page.getByRole('button', {name: 'Lượt xem', exact: true}).click();
  await expect(page.getByRole('cell', {name: 'Channel 250', exact: true})).toBeVisible();
  await page.getByRole('combobox', {name: 'Lượt quét', exact: true}).selectOption('1');
  await expect(page.getByText('Lượt quét #1', {exact: true})).toBeVisible();
  await expect(page.getByRole('cell', {name: 'Earlier channel', exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Mở Excel', exact: true})).toHaveCount(0);
  expect(downloads).toEqual([]);
  await page.screenshot({path: '../artifacts/ui/result-history.png', fullPage: true});
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    let status = 'ready';
    const state = () => ({status, completed: 0, total: 3, matches: 0, elapsed: 0, rows: [], logs: [], error: '', output: false, update: {status: 'current', message: 'Bạn đang dùng bản mới nhất.', progress: 0}});
    window.pywebview = {api: Object.fromEntries(Object.entries({
      get_bootstrap: () => ({version: '1.0.2', build: 'ui-test', has_api_key: true, keywords: localStorage.getItem('test-keywords') ?? 'AI Automation\nAI Agent\ntạo video bằng AI'}),
      get_state: state,
      save_preferences: () => true,
      set_keywords_dirty: () => true,
      save_keywords: (text: unknown) => {localStorage.setItem('test-keywords', String(text)); return text;},
      list_results: () => [{id: 2, created: '2026-10-17T00:00:00Z', status: 'stopped', count: 251, error: ''}, {id: 1, created: '2026-10-16T00:00:00Z', status: 'complete', count: 1, error: ''}],
      open_results: (id: unknown) => ({filename: `Lượt quét #${id}`, sheets: [`Lượt quét #${id}`], internal: true, run_id: id}),
      results_page: (_sheet: unknown, query: unknown, page: unknown, sort: unknown, descending: unknown) => {
        let rows = String(_sheet).endsWith('#1') ? [['Earlier channel', 7]] : Array.from({length: 251}, (_, i) => [`Channel ${i}`, i]);
        if (query) rows = rows.filter(row => String(row[0]).includes(String(query)));
        if (sort !== null && descending) rows.reverse();
        return {columns: ['Tên Kênh', 'Lượt xem'], rows: rows.slice(Number(page) * 100, (Number(page) + 1) * 100), page: Number(page), pages: Math.max(1, Math.ceil(rows.length / 100)), total: rows.length, original_total: String(_sheet).endsWith('#1') ? 1 : 251};
      },
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
  await page.getByRole('button', {name: 'Sửa bảng từ khóa', exact: true}).click();
  await page.getByRole('button', {name: 'Nhập từ file cũ', exact: true}).click();
  await expect(page.getByRole('cell', {name: 'beta', exact: true})).toBeVisible();
  await page.getByRole('textbox', {name: 'Tìm trong bảng'}).fill('alpha');
  await expect(page.getByRole('cell', {name: 'beta', exact: true})).toHaveCount(0);
  await page.getByRole('button', {name: 'Nhập cột từ khóa'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', {name: 'Xác nhận', exact: true}).click();
  await expect(page.getByRole('textbox', {name: 'Từ khóa dòng 1', exact: true})).toHaveValue('alpha');
  await page.getByRole('button', {name: 'Dùng để quét'}).click();
  await expect(page.getByRole('textbox', {name: 'Danh sách từ khóa'})).toHaveValue('alpha\nbeta');
});
