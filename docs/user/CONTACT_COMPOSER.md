# Contacting Channels from YTB-BOT

This feature is in the React desktop: **Results → View full details → Compose contact**. The application uses contact details from saved history for the exact Channel ID. No Excel download is needed.

## Gmail / Google Workspace

For a step-by-step Vietnamese setup and token lifecycle guide, see [Cách dùng Google OAuth 2.0](GOOGLE_OAUTH_VI.md).

### Initial Google setup

1. Open [Google Cloud Console](https://console.cloud.google.com/), create/select a project, and enable **Gmail API**. A YouTube API key does not replace Gmail OAuth configuration.
2. Open **Google Auth Platform** and configure Branding, Audience, and Data Access. Allow `openid`, `https://www.googleapis.com/auth/userinfo.email`, and `https://www.googleapis.com/auth/gmail.send`. The application does not request inbox read access.
3. If Audience is in **Testing** mode, add the sending addresses to **Test users**. Google may require application verification for wider distribution; Google Workspace may require administrator approval.
4. Create **OAuth Client ID → Desktop app** and download the JSON file. Do not select Web application.
5. In the composer, open **Set up your first connection → Import OAuth JSON file** and select the downloaded file. Do not upload it to GitHub. Once configured, the section reads **OAuth configuration is ready**, and **Change OAuth JSON file** replaces the import action.
6. Select **Connect Gmail**. The application opens your default browser to select a Google account and grant permission. The session waits up to three minutes. You can connect multiple accounts, then select a sender from the list.

Do not sign into Google inside the application's WebView. OAuth uses Google's library, a localhost callback with a dynamic port, PKCE, state validation, and email identity verification. The callback is not recorded in application logs.

### Composing and sending

1. Select a saved channel email as the **Recipient contact**.
2. Select a connected **Sender account**. The From address comes from the verified Google account and cannot be entered arbitrarily.
3. Enter a subject (up to 200 characters) and plain-text body (up to 50,000 characters). This version does not support attachments.
4. Choose **Save draft** to continue later, or **Review email** to save and check the channel name, From, To, subject, and body.
5. Select **Send email** to send directly through Gmail API. Each send has one recipient.

Closing a changed composer offers to save, discard changes, or continue editing. Closing the desktop with an unsaved draft requires confirmation. Application updates are blocked while drafts remain unsaved or an email is being sent.

### History and duplicate-send protection

History for each Channel ID appears below the composer and shows up to the 20 most recent attempts. Statuses are:

- **Gmail accepted request**: Gmail returned a message ID; this does not confirm recipient delivery.
- **Gmail rejected request**: the API returned an explicit rejection error.
- **Outcome unknown**: a timeout, network error, or indeterminate response. Check **Sent** in Gmail before trying again.
- **Sending / outcome unknown**: a request is running, or the application closed before recording the response.

Each draft revision permits only one send attempt, even with repeated clicks or after reopening the application. Send requests are not retried automatically. Accepted, sending, and uncertain email attempts block another send to the same Channel ID across individual and bulk workflows, including when the message, sender account, or recipient address changes. Editing a draft does not bypass this protection. A definitively rejected individual request may be edited and reviewed as a new revision. Saving unchanged content does not create a new revision.

Open **Discovery results → Email contact history** to search saved email requests by channel name, Channel ID, or recipient. This list includes provider acceptance, rejection, and uncertain outcomes; acceptance does not confirm delivery. These records and duplicate-send claims survive **Clear scan history** and restarting the app. They also cover existing saved send records from earlier versions. The protection depends on retaining the workspace database; it cannot reconstruct emails sent outside the bot or records from a deleted database.

In **Grouped contacts**, select unwanted email entries marked **Gmail rejected the request**, then choose **Remove selected failed emails** and confirm. Only selected addresses whose latest outcome is `failed` are removed from the queue; uncertain outcomes and other contact links are preserved. Removal persists after rescanning or clearing scan history, and stale reviewed drafts cannot send to those addresses. Send records remain available in email history. A rejected request does not by itself prove an address is invalid; it can also reflect account or permission problems.

## Bulk Gmail across saved channels

Open **Results > Grouped contacts** beside Scan history. Contact groups cover saved channels across scan history, using the latest saved row for each Channel ID; they are independent of the current table page, search, and sort. Equal normalized email addresses form one group with all matching channels. Normalization ignores case and surrounding whitespace; it does not merge Gmail dot or plus aliases. Social links appear as read-only groups and cannot become email recipients.

1. Select email groups, choose **Compose bulk email**, and select a connected Gmail sender. Review the associated channels before selecting a shared address.
2. Enter one subject and plain-text body. Each selected email receives a separate message with one To address, without CC/BCC or a shared recipient list.
3. Choose **Preview batch** and review its saved sender, complete recipient list, subject, and body. Preparation does not send mail. Editing requires a fresh review.
4. Choose **Send batch** to explicitly start the reviewed batch. The application allows at most **100 selected email groups per batch** and sends sequentially, with a **two-second pause between requests**. These are application safeguards, not Gmail provider limits or a guarantee of available quota.
5. Watch recipient progress. **Stop batch** prevents subsequent requests after the current request finishes; it cannot retract a request already submitted to Gmail.

Open **Batch history** to inspect saved batches. The application persists the reviewed batch and each recipient outcome in local SQLite storage. Previously attempted addresses for the same sender are skipped, including attempts made through the single-channel composer. A started batch cannot be started again. Restarting the desktop does not automatically resume an interrupted batch.

Recipient outcomes distinguish pending/sending, Gmail accepted request, failed/rejected, outcome unknown, skipped, and canceled before sending. **Accepted means Gmail returned a message ID; it does not guarantee delivery.** A timeout or interrupted request can already have reached Gmail. Check Gmail Sent manually before further contact. The application does not retry send requests automatically or read your inbox to reconcile them. On an error or uncertain outcome it stops the remaining requests and keeps their statuses for review.

### Gmail limits and responsible sending

Gmail API request quotas and mailbox sending limits are separate. Mailbox limits vary by account and are shared with other clients using that account; this application cannot show a reliable remaining daily allowance. A batch below the application cap can still be rejected or limited. See Google's [API usage limits](https://developers.google.com/workspace/gmail/api/reference/quota), [mail sending errors](https://developers.google.com/workspace/gmail/api/guides/handle-errors), and [Google Workspace sending limits](https://support.google.com/a/answer/166852).

Review Google's [email sender guidelines](https://support.google.com/mail/answer/81126) before sending. Use relevant messages, an accurate sender identity, and respect requests to stop contact. Public contact availability does not establish interest in receiving email. This plain-text composer does not manage recipient preferences or provide automated unsubscribe handling.

## Facebook and social contacts

### Connect your accounts

Open **Results → Grouped contacts → Linked accounts**. Gmail accounts can be configured, connected and disconnected here as well as in the email composer.

For Facebook, use a **Fanpage**, a Meta developer application configured for Messenger, and a **Page access token** with the Page's messaging permissions (`pages_messaging`, and the permissions required by Meta for reading Page conversations). Your account must have the appropriate Page task/access. Development mode is limited to permitted app roles/test recipients; broader use may require Meta App Review and advanced access.

Generate a Page access token for the intended Page through your Meta application setup / Graph API Explorer. Enter it in **Page access token → Connect Fanpage**. The bot validates Page identity and conversation access before saving it. This version uses developer-token setup; it does not provide a Facebook login popup. An expired or revoked token must be replaced by reconnecting the Page. Never share the token in screenshots, support messages or source control.

### Match a recipient and send

1. In a saved Facebook contact group, choose **Message [channel name]**.
2. Select your sending Fanpage and the existing Page conversation that belongs to that channel. Check the participant identity carefully: matching is your explicit decision, not an automatic guess based on names or public links.
3. Enter a plain-text Messenger message of up to 2,000 characters.
4. Select **Review Messenger message** to link the conversation and inspect the Page, recipient and immutable message snapshot.
5. Select **Send Messenger message**. The bot verifies eligibility again and submits the request automatically. Scanning does not send messages.

The standard send flow requires the recipient to have messaged the Page in the preceding **24 hours**. A public Facebook URL alone is not enough to obtain a Page-scoped recipient ID or initiate an API conversation. Ineligible conversations are disabled. If no conversation appears, ask the recipient to message the Page, then reopen the composer. The desktop synchronizes through Meta's Conversations API; no public webhook server is required. Large or unverifiable conversation histories are blocked conservatively.

**Accepted** means Meta returned a message ID, not confirmed delivery. Failed or uncertain sends remain in the queue. Check your Page inbox after an uncertain send; the application never automatically retries it. A durable Page/recipient claim prevents another attempt to the same recipient, including after restarting the bot. A failed request also requires reviewing the inbox and resolving the issue outside this version's send workflow; there is no reset-claim button.

Other social platforms retain the manual flow in the channel composer: compose → **Copy message** → **Open contact**. Opening a profile is not recorded as successful contact.

### Select all and automatic cleanup

**Select all visible email groups** applies to the current search/type filter. Selections outside the filter remain selected; deselecting all removes only visible email groups. The checkbox shows a mixed state for partial selection, and total selection remains limited to 100 groups.

When Gmail or Messenger accepts a send request, the contacted channels and **all their alternative email/social contacts** disappear from Grouped contacts. Accepted recipients in a shared email batch remove every channel in that recipient's reviewed snapshot. Other channels remain. This applies to accepted historical sends too, including sends recorded before this feature was installed.

Cleanup is persistent across refreshes, new scans and restarts. It removes channels from the contact work queue, preserving scan results and immutable send history. Unknown, failed, canceled and skipped outcomes do not trigger cleanup. Refresh contacts or close the send composer to see the updated queue.

See Meta's [Messenger API documentation](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api) and [Conversations API](https://www.postman.com/meta/messenger-platform-api/folder/22794852-255610cd-47f5-4f4d-b3fa-71aec360be9a). The client pins Graph API `v25.0`; recheck Meta's version support and application permissions when setting up your Page.

## Local data

- Drafts and send history share local storage at `%LOCALAPPDATA%/Ytb-Bot/data/workspace.sqlite3`. Each channel has one current draft.
- OAuth configuration and tokens are stored at `%LOCALAPPDATA%/Ytb-Bot/data/mail/credentials.bin`, encrypted with Windows DPAPI for the current Windows account. They are not stored in SQLite, `.env`, the frontend, or the EXE.
- The account list sent to React includes only account IDs and email addresses, without tokens or client secrets.
- Fanpage tokens use a separate DPAPI vault at `%LOCALAPPDATA%/Ytb-Bot/data/facebook/credentials.bin`. Public Page state contains only IDs and names. The masked input is cleared on submission; tokens are not retained in browser storage or SQLite.
- **Remove account from the bot** deletes local credentials. To revoke permission at Google, use [Google account connections](https://myaccount.google.com/connections).
- Credential protection currently supports Windows. Before configuring OAuth, you can still compose/save drafts and use social contact actions.

## Testing and verification limits

Python tests use mocked Gmail: OAuth/PKCE identity, Vietnamese MIME data, real DPAPI encryption, draft storage, duplicate-send protection, network errors, and link protection. Browser tests use a mocked bridge to check composing/saving/reviewing/sending and narrow layouts. Tests do not send real email.

Real sign-in and sending checks require your OAuth client and a test mailbox you control; do not use channel addresses for testing.

Messenger tests mock Meta requests and cover Page validation, pagination, eligibility, explicit matching, immutable reviews, concurrent submissions, uncertain outcomes and accepted-only cleanup. Browser tests mock the desktop bridge. Live Page connection and delivery require your Meta application, permissions and a test conversation; automated tests do not send real Facebook messages.

Official documentation: [Sending with Gmail](https://developers.google.com/workspace/gmail/api/guides/sending), [Gmail OAuth for Python desktop applications](https://developers.google.com/workspace/gmail/api/quickstart/python), [Desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app).
