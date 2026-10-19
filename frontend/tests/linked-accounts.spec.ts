import {expect, test} from '@playwright/test';

test.beforeEach(async ({page}) => {
  await page.addInitScript(() => {
    const groups = Array.from({length: 105}, (_, index) => ({id: String(index), kind: 'email', value: `user${index}@example.com`, channels: [{id: String(index), name: `Creator ${index}`}], last_status: '', last_created: ''}));
    groups.push({id: 'fb', kind: 'social', value: 'https://facebook.com/creator', channels: [{id: 'fb', name: 'Facebook creator'}], last_status: '', last_created: ''});
    let pages: {id: string; name: string}[] = [];
    let sent = false;
    let mode = '';
    const methods: Record<string, (...args: any[]) => unknown> = {
      get_bootstrap: () => ({version: '1.0.2', build: 'test', has_api_key: true, keywords: 'AI'}),
      get_state: () => ({status: 'ready', completed: 0, total: 0, matches: 0, elapsed: 0, rows: [], logs: [], error: '', output: false, update: {status: 'current', message: '', progress: 0}}),
      list_results: () => [], save_preferences: () => true, set_language: () => true, set_keywords_dirty: () => true,
      get_mail_state: () => ({configured: true, connecting: false, error: '', accounts: [{id: 'me', email: 'me@example.com'}]}),
      list_bulk_mail: () => [], contact_groups: () => groups.filter(g => !sent || g.id !== 'fb'),
      facebook_state: () => ({accounts: pages}),
      connect_facebook: (token: string) => {if (token !== 'valid-token') throw Error('Unable to connect the Page.'); pages = [{id: 'page1', name: 'My Page'}]; return {accounts: pages};},
      disconnect_facebook: () => {pages = []; return {accounts: pages};},
      facebook_conversations: () => [{id: 'conv', recipient_id: 'person', name: 'Creator', eligible: mode !== 'expired'}],
      bind_facebook_contact: () => true,
      prepare_facebook_message: (_id: string, payload: any) => ({id: 'draft', page_name: 'My Page', recipient_name: 'Creator', body: payload.body}),
      send_facebook_message: () => {if (mode === 'uncertain') throw Error('Bridge disconnected'); sent = true; return {status: 'accepted', message: 'Messenger accepted the request. Delivery is not confirmed.'};},
      facebook_history: () => [], set_facebook_dirty: () => true,
      test_set_mode: (value: string) => {mode = value;},
    };
    window.pywebview = {api: Object.fromEntries(Object.entries(methods).map(([name, method]) => [name, async (...args: unknown[]) => {
      try {return {ok: true, data: method(...args)};} catch (error) {return {ok: false, error: String(error)};}
    }]))};
  });
  await page.goto('/');
  await page.getByRole('button', {name: /View results in the bot/}).click();
  await page.getByRole('button', {name: 'Grouped contacts', exact: true}).click();
});

test('select all respects filters, mixed state, hidden selection and 100 limit', async ({page}) => {
  const all = page.getByRole('checkbox', {name: 'Select all visible email groups'});
  await all.click();
  await expect(page.locator('.contact-selection-bar [role=status]')).toContainText('100 selected');
  await expect(all).toHaveJSProperty('indeterminate', true);
  await page.getByRole('textbox', {name: 'Search contacts'}).fill('user0@');
  await expect(all).toBeChecked();
  await all.uncheck();
  await expect(page.locator('.contact-selection-bar [role=status]')).toContainText('99 selected');
  await page.getByRole('textbox', {name: 'Search contacts'}).fill('https://');
  await expect(all).toBeDisabled();
});

test('Gmail callback completion is polled and updates the sender list', async ({page}) => {
  await page.evaluate(() => {
    let connecting = false;
    let connected = false;
    window.pywebview!.api.get_mail_state = async () => ({ok: true, data: {
      configured: true, connecting, error: '',
      accounts: connected ? [{id: 'oauth', email: 'oauth@example.com'}] : [],
    }});
    window.pywebview!.api.connect_gmail = async () => {
      connecting = true;
      return {ok: true, data: true};
    };
    window.pywebview!.api.test_finish_gmail = async () => {
      connecting = false; connected = true;
      return {ok: true, data: true};
    };
  });
  await page.getByText('Linked accounts', {exact: true}).click();
  await page.getByRole('button', {name: 'Connect Gmail', exact: true}).click();
  await expect(page.getByRole('button', {name: 'Connecting…', exact: true})).toBeDisabled();
  await page.evaluate(() => window.pywebview!.api.test_finish_gmail());
  await expect(page.getByText('oauth@example.com', {exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Connect Gmail', exact: true})).toBeEnabled();
  await expect(page.getByText('Connect a Gmail sender in Linked accounts first.', {exact: true})).toHaveCount(0);
});

test('connect a Page, match a conversation, review and submit a Messenger message', async ({page}) => {
  await page.getByText('Linked accounts', {exact: true}).click();
  const token = page.getByLabel('Page access token', {exact: true});
  await expect(token).toHaveAttribute('type', 'password');
  await token.fill('bad');
  await page.getByRole('button', {name: 'Connect Fanpage', exact: true}).click();
  await expect(page.getByRole('alert')).toContainText('Unable to connect');
  await token.fill('valid-token');
  await page.getByRole('button', {name: 'Connect Fanpage', exact: true}).click();
  await expect(token).toHaveValue('');
  await expect(page.getByText('My Page', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Message Facebook creator'}).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Page conversation', {exact: true}).selectOption('conv');
  await dialog.getByLabel('Messenger message', {exact: true}).fill('Hello creator');
  await dialog.getByRole('button', {name: 'Review Messenger message'}).click();
  await expect(dialog).toContainText('Hello creator');
  await dialog.getByRole('button', {name: 'Send Messenger message', exact: true}).click();
  await expect(dialog).toContainText('Delivery is not confirmed');
  await expect(dialog.getByRole('button', {name: 'Send Messenger message', exact: true})).toHaveCount(0);
  await dialog.getByRole('button', {name: 'Close Messenger composer'}).click();
  await expect(page.getByText('https://facebook.com/creator', {exact: true})).toHaveCount(0);
});

test('Page disconnect and expired conversation prevent sending', async ({page}) => {
  await page.getByText('Linked accounts', {exact: true}).click();
  await page.getByLabel('Page access token', {exact: true}).fill('valid-token');
  await page.getByRole('button', {name: 'Connect Fanpage', exact: true}).click();
  await page.evaluate(async () => window.pywebview!.api.test_set_mode('expired'));
  await page.getByRole('button', {name: 'Message Facebook creator'}).click();
  await expect(page.getByRole('option', {name: /Messaging unavailable/})).toHaveJSProperty('disabled', true);
  await expect(page.getByRole('button', {name: 'Review Messenger message'})).toBeDisabled();
  await page.getByRole('button', {name: 'Close Messenger composer'}).click();
  await page.getByRole('region', {name: 'Facebook Fanpages'}).getByRole('button', {name: 'Disconnect'}).click();
  await expect(page.getByText('My Page', {exact: true})).toHaveCount(0);
});

test('narrow composer guards unsaved text and uncertain sends cannot be retried', async ({page}, testInfo) => {
  await page.setViewportSize({width: 375, height: 812});
  await page.getByText('Linked accounts', {exact: true}).click();
  await page.getByLabel('Page access token', {exact: true}).fill('valid-token');
  await page.getByRole('button', {name: 'Connect Fanpage', exact: true}).click();
  await page.evaluate(async () => window.pywebview!.api.test_set_mode('uncertain'));
  await page.getByRole('button', {name: 'Message Facebook creator'}).click();
  await page.getByLabel('Page conversation', {exact: true}).selectOption('conv');
  await page.getByRole('textbox', {name: 'Messenger message', exact: true}).fill('Keep this text');
  await page.keyboard.press('Escape');
  await expect(page.getByText('Discard the unsent Messenger draft?')).toBeVisible();
  await page.getByRole('button', {name: 'Keep editing'}).click();
  await expect(page.getByRole('textbox', {name: 'Messenger message', exact: true})).toHaveValue('Keep this text');
  await page.getByRole('button', {name: 'Review Messenger message'}).click();
  await page.getByRole('button', {name: 'Send Messenger message', exact: true}).click();
  await expect(page.getByRole('dialog')).toContainText('Messenger outcome is uncertain');
  await expect(page.getByRole('button', {name: 'Send Messenger message', exact: true})).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
  await page.screenshot({path: testInfo.outputPath('messenger-narrow.png')});
});
