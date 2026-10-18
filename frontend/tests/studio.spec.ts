import { expect, test } from '@playwright/test';

test('wide result tables keep trailing fields reachable inside the workspace', async ({page}) => {
  await page.setViewportSize({width: 1280, height: 720});
  await page.evaluate(() => {
    window.pywebview!.api.results_page = async () => ({ok: true, data: {
      columns: ['Tên Kênh', 'Channel ID', 'URL Kênh', 'Từ Khóa Quét', 'Ngày Tạo', 'Tuổi Kênh (Ngày)', 'Subscribers', 'Tổng Lượt Xem', 'Tổng Video', 'Video Gần Nhất', 'Email', 'Facebook', 'Liên Hệ Khác'],
      rows: [['A channel with a long name', 'UC' + 'a'.repeat(22), 'https://www.youtube.com/channel/UC' + 'a'.repeat(22), 'AI Agent', '2026-10-06', 12, 23, 123456, 18, 'A detailed video title '.repeat(16), 'hello@example.com', 'https://facebook.com/creator', 'https://t.me/myteam']],
      page: 0, pages: 1, total: 1, original_total: 1,
    }});
  });
  await page.getByRole('button', {name: /Xem kết quả trong Bot/}).click();
  await expect(page.getByRole('columnheader', {name: 'Video Gần Nhất'})).toBeVisible();
  const bounds = await page.locator('.workbook-panel .table-scroll').evaluate(element => {
    const rect = element.getBoundingClientRect();
    return {right: rect.right, width: rect.width, viewport: innerWidth, scrollable: element.scrollWidth > element.clientWidth};
  });
  expect(bounds.right).toBeLessThanOrEqual(bounds.viewport);
  expect(bounds.scrollable).toBe(true);
  await page.getByRole('button', {name: 'Cuộn sang phải', exact: true}).click();
  await expect.poll(() => page.locator('.workbook-panel .table-scroll').evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  await page.locator('.workbook-panel .table-scroll').evaluate(element => {element.scrollLeft = element.scrollWidth;});
  await expect(page.getByRole('button', {name: 'Cuộn sang phải', exact: true})).toBeDisabled();
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/results-wide.png'});
  await page.getByRole('button', {name: 'Xem đầy đủ dòng 1', exact: true}).click();
  await expect(page.getByRole('dialog', {name: 'Chi tiết kết quả'})).toBeVisible();
  await expect(page.getByRole('dialog').getByText('123456', {exact: true})).toBeVisible();
  await expect(page.getByRole('dialog').locator('dd').nth(9)).toHaveText('A detailed video title '.repeat(16).trim());
  await expect(page.getByRole('dialog').getByText('hello@example.com', {exact: true})).toBeAttached();
  await expect(page.getByRole('dialog').locator('dd').last()).toHaveText('https://t.me/myteam');
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/result-details.png'});
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  for (const width of [800, 375]) {
    await page.setViewportSize({width, height: 720});
    expect(await page.locator('.workbook-panel .table-scroll').evaluate(element => element.getBoundingClientRect().right <= innerWidth)).toBe(true);
  }
});

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
  await expect(page.getByRole('textbox', {name: 'Từ khóa dòng 5', exact: true})).toBeFocused();
  await expect(page.getByText(/Có thay đổi chưa lưu/)).toBeVisible();
  expect(downloads).toEqual([]);
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/keyword-editor.png', fullPage: true});
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
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/result-history.png', fullPage: true});
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
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/react-dark.png', fullPage: true});
  await page.getByRole('button', {name: 'Chuyển giao diện sáng'}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/react-light.png', fullPage: true});
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

test('drawer traps keyboard focus and returns it to the trigger', async ({page}) => {
  await page.setViewportSize({width: 800, height: 650});
  const trigger = page.getByRole('button', {name: 'Mở menu và bộ lọc'});
  await trigger.click();
  await expect(trigger).toHaveAttribute('aria-expanded', 'true');
  const close = page.getByRole('button', {name: 'Đóng menu', exact: true});
  await expect(close).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(page.getByRole('button', {name: 'Kiểm tra cập nhật', exact: true})).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(close).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(trigger).toBeFocused();
  await expect(trigger).toHaveAttribute('aria-expanded', 'false');
  expect(await page.locator('main').evaluate(element => element.inert)).toBe(false);
});

test('short laptop layouts keep the primary action visible without page overflow', async ({page}) => {
  for (const viewport of [{width: 1280, height: 720}, {width: 1024, height: 768}, {width: 375, height: 812}]) {
    await page.setViewportSize(viewport);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    if (viewport.width > 840) {
      const button = await page.getByRole('button', {name: /Bắt đầu khám phá/}).boundingBox();
      expect(button!.y + button!.height).toBeLessThanOrEqual(viewport.height);
    }
  }
  await page.setViewportSize({width: 1280, height: 720});
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/studio-laptop.png', fullPage: true});
  await page.getByRole('button', {name: 'Sửa bảng từ khóa', exact: true}).click();
  await expect(page.getByRole('heading', {level: 1})).toHaveText('Mọi ý tưởng, một nơi lưu.');
  await expect(page.getByRole('region', {name: 'Số liệu lượt quét'})).toHaveCount(0);
  await expect(page.getByRole('textbox', {name: 'Từ khóa dòng 1', exact: true})).toBeVisible();
});

test('result errors have an inline retry and empty history offers a clear next action', async ({page}) => {
  await page.evaluate(() => {window.pywebview!.api.list_results = async () => ({ok: false, error: 'History unavailable'});});
  await page.getByRole('button', {name: /Xem kết quả trong Bot/}).click();
  await expect(page.getByRole('alert').filter({hasText: 'Chưa đọc được lịch sử.'})).toBeVisible();
  await page.evaluate(() => {window.pywebview!.api.list_results = async () => ({ok: true, data: []});});
  await page.getByRole('button', {name: 'Làm mới', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Chưa có lượt khám phá nào'})).toBeVisible();
  await page.getByRole('button', {name: 'Bắt đầu lượt đầu tiên'}).click();
  await expect(page.getByRole('heading', {level: 1})).toHaveText('Khám phá kênh mới.');
});

test('text contrast remains readable in both themes', async ({page}) => {
  await page.emulateMedia({reducedMotion: 'reduce'});
  const contrast = async () => page.evaluate(() => {
    function luminance(color: string) {
      const values = color.match(/[\d.]+/g)!.slice(0, 3).map(Number).map(value => {
        const channel = value / 255;
        return channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4;
      });
      return values[0] * .2126 + values[1] * .7152 + values[2] * .0722;
    }
    function ratio(foreground: string, background: string) {
      const a = luminance(foreground); const b = luminance(background);
      return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
    }
    const button = getComputedStyle(document.querySelector('.start-button')!);
    const nav = getComputedStyle(document.querySelector('.nav-item.active')!);
    const muted = getComputedStyle(document.querySelector('.log-placeholder p')!);
    const panel = getComputedStyle(document.querySelector('.activity-panel')!);
    return [ratio(button.color, button.backgroundColor), ratio(nav.color, nav.backgroundColor), ratio(muted.color, panel.backgroundColor)];
  });
  for (const value of await contrast()) expect(value).toBeGreaterThanOrEqual(4.5);
  await page.getByRole('button', {name: 'Chuyển giao diện sáng'}).click();
  for (const value of await contrast()) expect(value).toBeGreaterThanOrEqual(4.5);
});

test('table loading failures can be retried without showing stale rows', async ({page}) => {
  await page.evaluate(() => {window.pywebview!.api.results_page = async () => ({ok: false, error: 'Read failed'});});
  await page.getByRole('button', {name: /Xem kết quả trong Bot/}).click();
  await expect(page.getByRole('alert').filter({hasText: 'Chưa đọc được bảng dữ liệu.'})).toBeVisible();
  await page.evaluate(() => {window.pywebview!.api.results_page = async () => ({ok: true, data: {columns: ['Tên Kênh'], rows: [['Recovered channel']], page: 0, pages: 1, total: 1, original_total: 1}});});
  await page.getByRole('button', {name: 'Tải lại bảng', exact: true}).click();
  await expect(page.getByRole('cell', {name: 'Recovered channel', exact: true})).toBeVisible();
});
