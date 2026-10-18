# Preparing YTB-BOT for Commercialization

This document describes preparation and direction, not paid packages already sold or quality commitments already achieved.

## Customers and positioning

The product owner has selected **YouTube market researchers** as the priority audience. The positioning is a Windows application for topic-based channel discovery, public-data screening, and organizing research results. Pricing and the sales model have not been finalized.

The core value is the workflow **research topic → keywords → channel screening → metric review → save and revisit**, with working data stored locally. Outreach supports follow-up after research.

A key limitation of the current version: the scanner accepts only channels with public contact details and skips saved channels in later scans. This suits discovery of new channels but does not yet support comprehensive market surveys or growth tracking over time. Product descriptions must disclose this sampling limitation.

## Current state and plans

| Present in the source code | To establish before commercial operation |
| --- | --- |
| Windows desktop, scanning, and local storage | Priority research problems, pricing packages, and support scope |
| User-supplied API key | Key setup experience, quota responsibilities, and error messages |
| Gmail OAuth using user-imported JSON | Customer Gmail onboarding and representative-account testing |
| Drafts and send history | Support procedures for unknown send outcomes |
| EXE, checksum, and GitHub updates | Pilot releases, rollback, and customer distribution |
| Current Apache 2.0 LICENSE | Distribution model and appropriate commercial documentation |

The experience described here currently has no purchase/license-activation workflow. Do not advertise payments, cloud sync, team collaboration, subscriptions, or an SLA as existing features.

## Preparation milestones

### Product priorities for researchers

The following proposals require design and validation before implementation; they are not existing features:

- Allow research on channels without public contact details while retaining the contact filter as an option.
- Separate new-channel discovery from refreshing saved channel metrics; define time-based metric snapshots if growth measurement is needed.
- Record survey settings and time, search scope, and limitations clearly so researchers can interpret results correctly.
- Validate demand for topic-based research groups, notes, comparisons, and report exports through interviews/trials with target customers.

### 1. Stabilize the product

- Compare the [initial review report](../reviews/PROJECT_REVIEW_2026-10-18.md) with newer code and regression tests; a new commit alone does not establish that a defect is fixed.
- Test on a clean Windows installation: launch the EXE, scan, stop, save/reopen, compose/send, update, and recover data.
- Check multiple application instances, network failures, exhausted quota, and unknown send outcomes.
- Distinguish mocked results from real integration results in release notes.

### 2. Reduce setup effort

- Decide whether customers manage their own YouTube API key and Gmail OAuth or receive setup assistance from the product team.
- Write illustrated guides for first launch, Gmail connection, and common errors.
- Check Google's current requirements for the chosen OAuth/distribution approach before wider rollout; this document does not replace that verification.

### 3. Standardize commercial operations

- Establish pricing, the sales model, and any required usage entitlement mechanism; implement after finalizing the model.
- Publish support scope, contact channels, incident handling, and update policies.
- Prepare privacy information, customer terms, and license content for the chosen distribution; review them separately before publication.
- Assess Windows code signing, the release process, and how customers verify download sources.
- Keep versions/builds traceable; the EXE, checksum, and metadata must come from the same build.

### 4. Run a small customer pilot

Invite a group of YouTube market researchers to investigate a specific topic: create keywords, filter channels, review metrics, and reopen results. Assess shortlist usefulness, understanding of sampling limits, time to first result, setup completion rate, and support needs. Collect usage data only after deciding appropriate notice and choice mechanisms; telemetry is not added by default.

Expand distribution after addressing pilot issues and finalizing operational responsibilities. A professional README supports sales, but does not replace testing and support procedures.
