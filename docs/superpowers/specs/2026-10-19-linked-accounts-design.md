# Linked accounts and grouped contact cleanup

Status: approved by the user on 2026-10-19; implementation and verification tracked in the linked-accounts plan and execution ledger.

## Intent

Let the user connect their own Gmail accounts and Facebook Fanpages, compose messages in the bot, and have the bot submit reviewed messages automatically. Add select-all and remove successfully contacted channels from grouped contacts.

## Scope and decisions

- Keep the Python desktop backend, React frontend and SQLite workspace.
- Reuse existing Gmail OAuth and the Windows encrypted credential vault.
- Add a linked-accounts panel with Gmail and Facebook Page connections. Never return saved access tokens to the UI or include them in logs or exceptions.
- Initial social sending support is Facebook Fanpages, selected by the user. Other discovered social contacts remain visible; additional providers require their own integrations.
- Use Meta Messenger's official API. A discovered public profile URL does not establish a recipient's Page-scoped ID or permission to message them. Never infer a recipient ID from a URL or name.
- Connect a Page using a Page access token entered through a masked field. Validate Page identity and messaging access before saving it. This developer-token setup is the proposed first version; Facebook OAuth login would additionally require a configured Meta application and callback deployment.
- Read eligible conversations through the Page conversations API and allow explicit association of a conversation with a saved channel. Do not guess channel identity from display names. Use the latest inbound message to check the standard messaging window, and recheck before submitting. Show unavailable access or recipient eligibility clearly.
- Follow message pagination far enough to establish the latest inbound timestamp. If freshness, sender identity or eligibility cannot be established, block submission rather than guessing.
- Send only after the user reviews the sender, recipient and message and starts sending. Run the send work automatically after that action; scanning alone does not send messages.
- Record durable attempts before network submission and avoid automatic retries for uncertain outcomes. API acceptance is not delivery confirmation.
- No public webhook server is included in this desktop version. Conversation synchronization runs when requested and before sending. Explain required Meta permissions, app review/access and Page setup in user documentation.

## Grouped contacts

- Add a select-all checkbox with checked, unchecked and mixed states.
- Select the visible email groups under the current search/type filter, up to the existing 100-recipient batch limit. Preserve selections outside the filter and explain when the limit is reached.
- Facebook sends use the explicitly matched Page conversation, not the email bulk endpoint.
- After an accepted Gmail or Facebook send, remove every associated channel and all its contact details from grouped contacts, including alternate email addresses and social links.
- Persist this exclusion by channel ID so refreshing, restarting or older saved scans cannot bring the channel back into grouped contacts.
- Retain scan history and immutable send history. This is removal from the grouped-contact work queue, not deletion of historical scan records.
- Failed, canceled, skipped and unknown outcomes do not remove channels.
- Shared contact groups retain any channels that have not been successfully contacted. Accepted sends to a shared group remove all channels represented by that accepted recipient snapshot.
- Existing accepted send history is included when determining completed channels, so previously contacted channels are also removed.

## Components and order

1. Grouped-contact selection: frontend checkbox behavior, translations and browser checks.
2. Completed-channel exclusion: persistent state, accepted send integration for individual and bulk Gmail, backend tests.
3. Page accounts and conversations: Meta HTTP client, encrypted credentials, bridge methods, linked-account UI and explicit recipient matching.
4. Facebook submission: reviewed sends, durable attempts, eligibility checks and completion cleanup.
5. Documentation and verification.

## Verification

- Backend tests cover accepted-only cleanup, alternate contacts, shared groups, historical acceptance, persistence, recipient matching, Page credential validation and uncertain-send behavior.
- Mock external APIs; tests never send real messages or require live credentials.
- Browser tests cover select-all, mixed state, filters, selection limits, account forms and send state feedback.
- Run `python -m unittest discover -s tests`, `npm run build --prefix frontend` and appropriate Playwright tests using the repository configuration.
- Live Facebook connection and actual message delivery require the user's Page credentials and Meta app permissions. Report those separately from mocked verification.

## Review points

The user approved developer-token connection, explicit conversation matching and the complete description before implementation. Arbitrary first messages to every scraped Facebook URL are not supported by this design.

Independent builder review found no additional blocking questions. Review emphasized conservative pagination and the visibility of shared-contact and historical cleanup behavior.

## API references

- Meta Messenger API: https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api
- Meta Conversations API: https://www.postman.com/meta/messenger-platform-api/folder/22794852-255610cd-47f5-4f4d-b3fa-71aec360be9a
