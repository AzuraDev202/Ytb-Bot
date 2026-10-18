import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

async function contactFixture(page: Page, outcome = 'accepted', configured = true) {
  await page.evaluate(({outcome, configured}) => {
    const api = window.pywebview!.api;
    const sender = {id: 'sender', email: 'me@example.com'};
    let ready = configured;
    let connected = configured;
    api.results_page = async () => ({ok: true, data: {columns: ['Channel Name', 'Channel ID', 'Email', 'Facebook'], rows: [['Creator', 'creator', 'creator@example.com', 'https://facebook.com/creator']], page: 0, pages: 1, total: 1, original_total: 1}});
    api.get_mail_state = async () => ({ok: true, data: {configured: ready, connecting: false, error: '', accounts: connected ? [sender] : []}});
    api.configure_gmail = async () => {ready = true; return api.get_mail_state();};
    api.connect_gmail = async () => {connected = true; return {ok: true, data: true};};
    api.set_contact_dirty = async () => ({ok: true, data: true});
    api.contact_context = async () => ({ok: true, data: {channel_id: 'creator', name: 'Creator', contacts: [
      {kind: 'email', label: 'Email', value: 'creator@example.com'}, {kind: 'social', label: 'Facebook', value: 'https://facebook.com/creator'}],
      draft: JSON.parse(localStorage.getItem('contact-draft') || 'null'), history: JSON.parse(localStorage.getItem('contact-history') || '[]')}});
    api.save_contact_draft = async (_channel, payload) => {
      const value = payload as {recipient: string; account_id: string; subject: string; body: string};
      const previous = JSON.parse(localStorage.getItem('contact-draft') || 'null');
      const revision = (previous?.revision || 0) + 1;
      const saved = {...value, revision}; localStorage.setItem('contact-draft', JSON.stringify(saved));
      return {ok: true, data: saved};
    };
    api.send_contact_mail = async (_channel, revision) => {
      localStorage.setItem('contact-send-count', String(Number(localStorage.getItem('contact-send-count') || 0) + 1));
      localStorage.setItem('contact-history', JSON.stringify([{id: 'attempt', revision, created: '2026-10-18T03:00:00Z', status: outcome, payload: JSON.parse(localStorage.getItem('contact-draft') || '{}'), message_id: outcome === 'accepted' ? 'gmail-message' : ''}]));
      return {ok: true, data: {status: outcome, message: outcome === 'accepted' ? 'Gmail accepted the send request.' : 'It is unclear whether Gmail accepted the message. Check Sent mail in Gmail before trying again.'}};
    };
    api.open_social_contact = async (_channel, target) => {localStorage.setItem('contact-social', String(target)); return {ok: true, data: true};};
  }, {outcome, configured});
}

async function openContact(page: Page) {
  await page.getByRole('button', {name: /View results in the bot/}).click();
  await page.getByRole('button', {name: 'View full row 1', exact: true}).click();
  await page.getByRole('button', {name: 'Compose contact', exact: true}).click();
  await expect(page.getByRole('dialog', {name: 'Compose contact', exact: true})).toBeVisible();
  await expect(page.getByRole('combobox', {name: 'Recipient contact', exact: true})).toBeVisible();
}

test('scan status changes and history errors preserve an unsaved contact draft', async ({page}) => {
  await contactFixture(page);
  await openContact(page);
  await page.getByRole('textbox', {name: 'Contact message'}).fill('Draft to preserve');
  await page.evaluate(() => {
    const api = window.pywebview!.api;
    const previous = api.get_state;
    api.get_state = async () => {
      const reply = await previous();
      return {...reply, data: {...reply.data as object, status: 'complete'}};
    };
    api.list_results = async () => ({ok: false, error: 'Temporary history failure'});
  });
  await expect(page.getByRole('alert').filter({hasText: 'Temporary history failure'})).toBeVisible();
  await expect(page.getByRole('dialog', {name: 'Compose contact', exact: true})).toBeVisible();
  await expect(page.getByRole('textbox', {name: 'Contact message'})).toHaveValue('Draft to preserve');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', {name: 'Save and close'})).toBeVisible();
});

test('contact composer saves drafts, previews sender and sends only after explicit confirmation', async ({page}) => {
  await page.setViewportSize({width: 1280, height: 720});
  await contactFixture(page);
  await openContact(page);
  await page.getByRole('textbox', {name: 'Email subject'}).fill('Collaboration with Creator');
  await page.getByRole('textbox', {name: 'Contact message'}).fill('Hello!\nI would like to discuss a project.');
  await page.getByRole('button', {name: 'Save draft', exact: true}).click();
  await page.getByRole('button', {name: 'Close composer'}).click();
  await page.getByRole('button', {name: 'View full row 1', exact: true}).click();
  await page.getByRole('button', {name: 'Compose contact', exact: true}).click();
  await expect(page.getByRole('textbox', {name: 'Contact message'})).toHaveValue('Hello!\nI would like to discuss a project.');
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/contact-composer.png'});
  await page.getByRole('button', {name: 'Review email', exact: true}).click();
  await expect(page.getByRole('region', {name: 'Review email'})).toContainText('me@example.com');
  expect(await page.evaluate(() => localStorage.getItem('contact-send-count'))).toBeNull();
  await page.getByRole('button', {name: 'Send email', exact: true}).click();
  await expect(page.getByRole('status').filter({hasText: 'Gmail accepted the send request.'})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Send email', exact: true})).toBeDisabled();
  expect(await page.evaluate(() => localStorage.getItem('contact-send-count'))).toBe('1');
});

test('contact composer handles unsaved drafts, uncertain delivery and narrow windows', async ({page}) => {
  await page.setViewportSize({width: 375, height: 720});
  await contactFixture(page, 'unknown');
  await openContact(page);
  await page.getByRole('textbox', {name: 'Email subject'}).fill('Hello');
  await page.getByRole('textbox', {name: 'Contact message'}).fill('Message');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', {name: 'Save and close'})).toBeVisible();
  await page.getByRole('button', {name: 'Keep editing'}).click();
  const box = await page.getByRole('dialog', {name: 'Compose contact', exact: true}).boundingBox();
  expect(box!.x + box!.width).toBeLessThanOrEqual(375);
  await page.getByRole('button', {name: 'Review email', exact: true}).click();
  await page.getByRole('button', {name: 'Send email', exact: true}).click();
  await expect(page.getByRole('status').filter({hasText: 'Unclear whether Gmail'})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Send email', exact: true})).toBeDisabled();
});

test('social contact handoff and first-time Gmail setup stay separate from sending email', async ({page}) => {
  await contactFixture(page, 'accepted', false);
  await openContact(page);
  await expect(page.getByRole('button', {name: 'Connect Gmail', exact: true})).toBeDisabled();
  await page.getByRole('button', {name: 'Import OAuth JSON file', exact: true}).click();
  await expect(page.getByRole('button', {name: 'Connect Gmail', exact: true})).toBeEnabled();
  await page.getByRole('button', {name: 'Connect Gmail', exact: true}).click();
  await expect(page.getByRole('combobox', {name: 'Sender account'}).getByRole('option', {name: 'me@example.com'})).toBeAttached();
  await page.getByRole('combobox', {name: 'Recipient contact', exact: true}).selectOption('https://facebook.com/creator');
  await expect(page.getByRole('textbox', {name: 'Email subject'})).toHaveCount(0);
  await page.getByRole('textbox', {name: 'Contact message'}).fill('Hello on Facebook');
  await page.getByRole('button', {name: 'Open contact', exact: true}).click();
  await expect.poll(() => page.evaluate(() => localStorage.getItem('contact-social'))).toBe('https://facebook.com/creator');
  expect(await page.evaluate(() => localStorage.getItem('contact-send-count'))).toBeNull();
});

test('wide result tables keep trailing fields reachable inside the workspace', async ({page}) => {
  await page.setViewportSize({width: 1280, height: 720});
  await page.evaluate(() => {
    window.pywebview!.api.results_page = async () => ({ok: true, data: {
      columns: ['Channel Name', 'Channel ID', 'Channel URL', 'Search Keyword', 'Created Date', 'Channel Age (Days)', 'Subscribers', 'Total Views', 'Total Videos', 'Latest Video', 'Email', 'Facebook', 'Other Contacts'],
      rows: [['A channel with a long name', 'UC' + 'a'.repeat(22), 'https://www.youtube.com/channel/UC' + 'a'.repeat(22), 'AI Agent', '2026-10-06', 12, 23, 123456, 18, 'A detailed video title '.repeat(16), 'hello@example.com', 'https://facebook.com/creator', 'https://t.me/myteam']],
      page: 0, pages: 1, total: 1, original_total: 1,
    }});
  });
  await page.getByRole('button', {name: /View results in the bot/}).click();
  await expect(page.getByRole('columnheader', {name: 'Latest Video'})).toBeVisible();
  const bounds = await page.locator('.workbook-panel .table-scroll').evaluate(element => {
    const rect = element.getBoundingClientRect();
    return {right: rect.right, width: rect.width, viewport: innerWidth, scrollable: element.scrollWidth > element.clientWidth};
  });
  expect(bounds.right).toBeLessThanOrEqual(bounds.viewport);
  expect(bounds.scrollable).toBe(true);
  await page.getByRole('button', {name: 'Scroll right', exact: true}).click();
  await expect.poll(() => page.locator('.workbook-panel .table-scroll').evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  await page.locator('.workbook-panel .table-scroll').evaluate(element => {element.scrollLeft = element.scrollWidth;});
  await expect(page.getByRole('button', {name: 'Scroll right', exact: true})).toBeDisabled();
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/results-wide.png'});
  await page.getByRole('button', {name: 'View full row 1', exact: true}).click();
  await expect(page.getByRole('dialog', {name: 'Result details'})).toBeVisible();
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
  await page.getByRole('button', {name: 'Edit keyword table', exact: true}).click();
  await page.getByRole('textbox', {name: 'Keyword row 1', exact: true}).evaluate(element => {
    const transfer = new DataTransfer(); transfer.setData('text/plain', 'New topic\tignored\nSecond topic\nThird topic');
    element.dispatchEvent(new ClipboardEvent('paste', {clipboardData: transfer, bubbles: true, cancelable: true}));
  });
  await expect(page.getByRole('textbox', {name: 'Keyword row 2', exact: true})).toHaveValue('Second topic');
  await page.getByRole('textbox', {name: 'Keyword row 2', exact: true}).fill('Edited topic');
  await page.getByRole('checkbox', {name: 'Select keyword 3', exact: true}).check();
  await page.getByRole('button', {name: 'Delete 1', exact: true}).click();
  await page.getByRole('button', {name: 'Confirm', exact: true}).click();
  await page.getByRole('button', {name: 'Save keywords', exact: true}).click();
  await expect(page.getByText(/Saved in the bot ·/)).toBeVisible();
  await page.reload();
  await page.getByRole('button', {name: 'Edit keyword table', exact: true}).click();
  await expect(page.getByRole('textbox', {name: 'Keyword row 1', exact: true})).toHaveValue('New topic');
  await expect(page.getByRole('textbox', {name: 'Keyword row 2', exact: true})).toHaveValue('Edited topic');
  await page.getByRole('button', {name: 'Add row', exact: true}).click();
  await expect(page.getByRole('textbox', {name: 'Keyword row 5', exact: true})).toBeFocused();
  await expect(page.getByText(/Unsaved changes/)).toBeVisible();
  expect(downloads).toEqual([]);
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/keyword-editor.png', fullPage: true});
});

test('browse result history, paginate, search and sort without downloads', async ({page}) => {
  const downloads: string[] = [];
  page.on('download', download => downloads.push(download.suggestedFilename()));
  await page.getByRole('button', {name: /View results in the bot/}).click();
  await expect(page.getByRole('cell', {name: 'Channel 0', exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Next page', exact: true}).click();
  await expect(page.getByRole('cell', {name: 'Channel 100', exact: true})).toBeVisible();
  await page.getByRole('textbox', {name: 'Search table'}).fill('Channel 250');
  await expect(page.getByRole('cell', {name: 'Channel 250', exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Clear search'}).click();
  await page.getByRole('button', {name: 'Views', exact: true}).click();
  await page.getByRole('button', {name: 'Views', exact: true}).click();
  await expect(page.getByRole('cell', {name: 'Channel 250', exact: true})).toBeVisible();
  await page.getByRole('combobox', {name: 'Scan', exact: true}).selectOption('1');
  await expect(page.getByText('Scan #1', {exact: true})).toBeVisible();
  await expect(page.getByRole('cell', {name: 'Earlier channel', exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Open Excel', exact: true})).toHaveCount(0);
  expect(downloads).toEqual([]);
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/result-history.png', fullPage: true});
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    let status = 'ready';
    const state = () => ({status, completed: 0, total: 3, matches: 0, elapsed: 0, rows: [], logs: [], error: '', output: false, update: {status: 'current', message: 'You are using the latest version.', progress: 0}});
    window.pywebview = {api: Object.fromEntries(Object.entries({
      get_bootstrap: () => ({version: '1.0.2', build: 'ui-test', has_api_key: true, keywords: localStorage.getItem('test-keywords') ?? 'AI Automation\nAI Agent\nAI video creation'}),
      get_state: state,
      save_preferences: () => true,
      set_keywords_dirty: () => true,
      save_keywords: (text: unknown) => {localStorage.setItem('test-keywords', String(text)); return text;},
      list_results: () => [{id: 2, created: '2026-10-17T00:00:00Z', status: 'stopped', count: 251, error: ''}, {id: 1, created: '2026-10-16T00:00:00Z', status: 'complete', count: 1, error: ''}],
      open_results: (id: unknown) => ({filename: `Scan #${id}`, sheets: [`Scan #${id}`], internal: true, run_id: id}),
      results_page: (_sheet: unknown, query: unknown, page: unknown, sort: unknown, descending: unknown) => {
        let rows = String(_sheet).endsWith('#1') ? [['Earlier channel', 7]] : Array.from({length: 251}, (_, i) => [`Channel ${i}`, i]);
        if (query) rows = rows.filter(row => String(row[0]).includes(String(query)));
        if (sort !== null && descending) rows.reverse();
        return {columns: ['Channel Name', 'Views'], rows: rows.slice(Number(page) * 100, (Number(page) + 1) * 100), page: Number(page), pages: Math.max(1, Math.ceil(rows.length / 100)), total: rows.length, original_total: String(_sheet).endsWith('#1') ? 1 : 251};
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
  await expect(page.getByText('Local processing', {exact: true})).toBeVisible();
});

test('theme, scan lifecycle and responsive layout', async ({page}) => {
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/react-dark.png', fullPage: true});
  await page.getByRole('button', {name: 'Switch to light theme'}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/react-light.png', fullPage: true});
  await page.getByRole('button', {name: /Start discovery/}).click();
  await expect(page.getByRole('button', {name: 'Stop', exact: true})).toBeEnabled();
  await page.getByRole('button', {name: 'Stop', exact: true}).click();
  await expect(page.getByRole('button', {name: /Start discovery/})).toBeEnabled();
  await page.setViewportSize({width: 800, height: 600});
  await expect(page.getByRole('button', {name: 'Open menu and filters'})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.locator('.sidebar')).toHaveCSS('visibility', 'hidden');
  await page.screenshot({path: '../artifacts/ui/react-compact.png', fullPage: true, animations: 'disabled'});
  await page.getByRole('button', {name: 'Open menu and filters'}).click();
  await expect(page.getByLabel('YouTube API Key', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Close menu', exact: true}).click();
  await expect(page.locator('.sidebar')).toHaveCSS('visibility', 'hidden');
});

test('Excel search and confirmed import use the original column', async ({page}) => {
  await page.getByRole('button', {name: 'Edit keyword table', exact: true}).click();
  await page.getByRole('button', {name: 'Import existing file', exact: true}).click();
  await expect(page.getByRole('cell', {name: 'beta', exact: true})).toBeVisible();
  await page.getByRole('textbox', {name: 'Search table'}).fill('alpha');
  await expect(page.getByRole('cell', {name: 'beta', exact: true})).toHaveCount(0);
  await page.getByRole('button', {name: 'Import keyword column'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', {name: 'Confirm', exact: true}).click();
  await expect(page.getByRole('textbox', {name: 'Keyword row 1', exact: true})).toHaveValue('alpha');
  await page.getByRole('button', {name: 'Use for scanning'}).click();
  await expect(page.getByRole('textbox', {name: 'Keyword list'})).toHaveValue('alpha\nbeta');
});

test('drawer traps keyboard focus and returns it to the trigger', async ({page}) => {
  await page.setViewportSize({width: 800, height: 650});
  const trigger = page.getByRole('button', {name: 'Open menu and filters'});
  await trigger.click();
  await expect(trigger).toHaveAttribute('aria-expanded', 'true');
  const close = page.getByRole('button', {name: 'Close menu', exact: true});
  await expect(close).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(page.getByRole('button', {name: 'Check for updates', exact: true})).toBeFocused();
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
      const button = await page.getByRole('button', {name: /Start discovery/}).boundingBox();
      expect(button!.y + button!.height).toBeLessThanOrEqual(viewport.height);
    }
  }
  await page.setViewportSize({width: 1280, height: 720});
  await page.screenshot({animations: 'disabled', path: '../artifacts/ui/studio-laptop.png', fullPage: true});
  await page.getByRole('button', {name: 'Edit keyword table', exact: true}).click();
  await expect(page.getByRole('heading', {level: 1})).toHaveText('Keyword list');
  await expect(page.getByRole('region', {name: 'Scan statistics'})).toHaveCount(0);
  await expect(page.getByRole('textbox', {name: 'Keyword row 1', exact: true})).toBeVisible();
});

test('result errors have an inline retry and empty history offers a clear next action', async ({page}) => {
  await page.evaluate(() => {window.pywebview!.api.list_results = async () => ({ok: false, error: 'History unavailable'});});
  await page.getByRole('button', {name: /View results in the bot/}).click();
  await expect(page.getByRole('alert').filter({hasText: 'Could not read the history.'})).toBeVisible();
  await page.evaluate(() => {window.pywebview!.api.list_results = async () => ({ok: true, data: []});});
  await page.getByRole('button', {name: 'Refresh', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'No discovery scans yet'})).toBeVisible();
  await page.getByRole('button', {name: 'Start your first scan'}).click();
  await expect(page.getByRole('heading', {level: 1})).toHaveText('Discover new channels');
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
  await page.getByRole('button', {name: 'Switch to light theme'}).click();
  for (const value of await contrast()) expect(value).toBeGreaterThanOrEqual(4.5);
});

test('table loading failures can be retried without showing stale rows', async ({page}) => {
  await page.evaluate(() => {window.pywebview!.api.results_page = async () => ({ok: false, error: 'Read failed'});});
  await page.getByRole('button', {name: /View results in the bot/}).click();
  await expect(page.getByRole('alert').filter({hasText: 'Could not read the table.'})).toBeVisible();
  await page.evaluate(() => {window.pywebview!.api.results_page = async () => ({ok: true, data: {columns: ['Channel Name'], rows: [['Recovered channel']], page: 0, pages: 1, total: 1, original_total: 1}});});
  await page.getByRole('button', {name: 'Reload table', exact: true}).click();
  await expect(page.getByRole('cell', {name: 'Recovered channel', exact: true})).toBeVisible();
});
