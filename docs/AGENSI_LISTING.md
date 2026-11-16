# Draft marketplace listing

Status: review candidate. Do not mark live until the channel pilot and Agensi
delivery/eligibility checks below pass. Source release: 0.3.0-beta.1.

## Title

Divithy YouTube Publisher — Reviewed Batch Uploads & Shorts Schedule

## Price

Suggested introductory price: USD 10, one-time. This is a test price, not an
estimate of demand. At Agensi's published 70% share, a USD 10 net sale yields
USD 7 before the creator's own taxes and any refunds. Tool usage fees are
separate and do not pay creator revenue under the current platform terms.

## Short description

Turn finished local video packages into a reviewed five-day YouTube queue.
Your agent validates metadata, shows dates and privacy settings, and uses the
local publisher to upload only after authorization. Includes safe resume and
thumbnail/playlist repair guidance.

## What buyers receive

An original agent workflow, setup/package guide, exact CLI operations and
recovery instructions for Divithy YouTube Publisher. Designed for creators
working with batches of main episodes plus three Shorts, including gaming
series and tutorial channels. Main-only packages are also supported.

The underlying application and this workflow are available as open-source MIT
code. Payment buys marketplace access and convenience; it does not make the
source exclusive or include personal setup services or a support SLA.

## Needs access to / prerequisites

- An agent that can run local shell commands and access the user's media.
- A separate local installation of Divithy YouTube Publisher 0.3 beta or later
  with --upload and --approve-plan support, plus Python 3.11+ and dependencies.
- The user's own Google Cloud project with YouTube Data API enabled, a Desktop
  OAuth client and browser authorization for a channel they own/manage.
- Ready MP4 files and approved metadata in the documented package layout.

The ZIP contains text instructions and references, not the application or a
hosted service. Agensi's shared keys do not replace channel OAuth. This skill
needs no paid Agensi model or data tools. Do not advertise universal compatibility
with agents that cannot access local files or run commands.

## Limits to display before purchase

Fixed five-day cadence; one main MP4 and zero or exactly three Shorts per
package. No video editing, thumbnail generation, arbitrary calendar editor,
caption upload, related-video linking, channel growth promise or distributed
duplicate prevention. API quotas and account limits apply. A failed request
with an unknown outcome requires manual YouTube Studio reconciliation.

## Example user request

“I have two finished episodes and three Shorts for each. Validate the packages,
show a five-day plan in Europe/Warsaw, and leave all uploads private for my first
test. Show me the metadata and correct channel before asking me to authorize
the first upload.”

## Checks before submission

- On an authorized test channel, complete a small private upload, check title,
  description, tags, thumbnail and playlist, and verify a future scheduled
  publication. The current automated suite uses fake API responses.
- Confirm Agensi accepts an original paid workflow around the author's own
  public MIT application, with the external local runtime disclosed.
- Test that the connector delivers both SKILL.md and references/workflow.md
  and that the target agent can use the local application. Platform docs say
  scripts are delivered individually as temporary files; this package avoids
  sibling-script imports by keeping the application a disclosed prerequisite.
- Set the listing version manually to 0.3.0-beta.1 if the upload form does not
  read metadata.version. Connect the seller payout method and complete review.
- Add a genuine demo from the pilot. Do not substitute fake automated-test
  output for an actual upload demonstration.

## Platform references checked 16 November 2026

- [Packaging](https://www.agensi.io/docs/packaging)
- [What can be sold](https://www.agensi.io/docs/what-you-can-sell)
- [Earnings](https://www.agensi.io/docs/earnings-and-payouts)
- [Creator terms](https://www.agensi.io/terms)

Visitor/user counts in outreach and examples of other sellers' revenue have
not been independently verified. Existing asking prices do not establish sales.
