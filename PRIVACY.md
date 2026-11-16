# Privacy Policy — Divithy Publisher

**Effective date:** 16 November 2026

Divithy Publisher is an open-source local application for people authorized to
manage a YouTube channel. Each operator uses their own local installation and
Google OAuth client. The developer does not operate a shared upload service,
customer account database or telemetry endpoint for this application.

## Data and purpose

After Google OAuth consent, the application uses YouTube Data API v3 to identify
the connected channel, upload selected videos, set their metadata and privacy or
scheduled publication dates, upload thumbnails, and find/create/update playlists.
The requested youtube scope is broader than upload-only access because playlist
management is included. The public application does not implement caption
uploads, automatic video deletion or access to unrelated Google services.

Media, metadata, OAuth credentials, tokens, approved plans and upload history
are stored on the operator's computer. Media, relevant metadata and authorized
API requests are transmitted to Google/YouTube to perform the operator's chosen
actions. The application has no mechanism to send these to its developer or
sell them to third parties. See the [Google Privacy Policy](https://policies.google.com/privacy).

## Local storage and deletion

Token and state files are excluded from the repository. Protect them and their
backups with appropriate OS permissions. POSIX files written by the application
use owner-only permissions; Windows access is governed by the containing user's
folder permissions. A state file contains filenames, planned metadata and YouTube
IDs and must be treated as private even though it is not an OAuth credential.

Revoke access through [Google Account connections](https://myaccount.google.com/connections)
and remove local token.json to disconnect. Local records remain until deleted by
the operator. Deleting them does not delete YouTube content; use YouTube Studio
to manage or delete uploaded content. Preserve or reconcile video IDs before
restarting after deleting history, to avoid duplicate uploads.

## Optional AI-agent and marketplace use

When an operator uses an AI agent or Agensi to orchestrate the local application,
those services process conversation and tool data under their own policies.
Keep OAuth JSON, tokens and authorization codes out of conversations. Review
which unpublished metadata an agent may read or display. The skill's marketplace
purchase does not authorize Google access or uploading videos.

## Contact

[michal@lemanczyk-it.pl](mailto:michal@lemanczyk-it.pl)

[Source repository](https://github.com/Divithy-IT/divithy-youtube-publisher)
