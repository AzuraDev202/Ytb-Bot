# Contacting Channels from YTB-BOT

This feature is in the React desktop: **Results → View full details → Compose contact**. The application uses contact details from saved history for the exact Channel ID. No Excel download is needed.

## Gmail / Google Workspace

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

Each draft revision permits only one send attempt, even with repeated clicks or after reopening the application. Send requests are not retried automatically. To send again, edit and save the content as a new revision, then review it. Saving unchanged content does not create a new revision.

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

Review Google's [email sender guidelines](https://support.google.com/mail/answer/81126) before outreach. Public contact availability does not establish interest in bulk mail. Relevant messages, accurate sender identity, respect for opt-outs, and domain authentication affect sender reputation and delivery. Google's additional bulk-sender requirements, including one-click unsubscribe for applicable marketing/subscription traffic, are not implemented by this plain-text outreach composer. An application cap does not certify compliance with sender requirements.

## Facebook and social contacts

Select a saved link → compose text → **Copy message** → **Open contact**. Paste and send the message on that platform using your account. The application does not send social messages automatically or record opening a profile as a sent email.

## Local data

- Drafts and send history share local storage at `%LOCALAPPDATA%/Ytb-Bot/data/workspace.sqlite3`. Each channel has one current draft.
- OAuth configuration and tokens are stored at `%LOCALAPPDATA%/Ytb-Bot/data/mail/credentials.bin`, encrypted with Windows DPAPI for the current Windows account. They are not stored in SQLite, `.env`, the frontend, or the EXE.
- The account list sent to React includes only account IDs and email addresses, without tokens or client secrets.
- **Remove account from the bot** deletes local credentials. To revoke permission at Google, use [Google account connections](https://myaccount.google.com/connections).
- Credential protection currently supports Windows. Before configuring OAuth, you can still compose/save drafts and use social contact actions.

## Testing and verification limits

Python tests use mocked Gmail: OAuth/PKCE identity, Vietnamese MIME data, real DPAPI encryption, draft storage, duplicate-send protection, network errors, and link protection. Browser tests use a mocked bridge to check composing/saving/reviewing/sending and narrow layouts. Tests do not send real email.

Real sign-in and sending checks require your OAuth client and a test mailbox you control; do not use channel addresses for testing.

Official documentation: [Sending with Gmail](https://developers.google.com/workspace/gmail/api/guides/sending), [Gmail OAuth for Python desktop applications](https://developers.google.com/workspace/gmail/api/quickstart/python), [Desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app).
