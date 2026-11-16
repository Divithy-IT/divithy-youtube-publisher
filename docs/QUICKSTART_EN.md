# YouTube Publisher: first run and recovery

This is a local application for a channel you own or manage. Python 3.11+ and
local file/shell access are required. The CLI works on Windows, Linux and macOS;
the optional desktop interface needs Tk (included in most python.org Windows
installations; an OS package such as python3-tk on Linux).

The supported workflow is deliberately specific: numbered folders, one main MP4,
and either zero or exactly three Shorts per folder. Two packages fill a five-day
cycle. Other series names work through gra.txt and playlist_names. This release
does not edit videos, generate thumbnails, choose arbitrary calendar slots,
verify Shorts dimensions, add related-video links, upload captions, or operate
as a hosted scheduler. Scheduling is sent to YouTube in advance; the computer
does not need to stay on after a completed upload.

## Install

Use the 0.3 beta candidate from the source repository (the old 0.2 CLI uploads
by default and must not be used with this workflow):

```sh
git clone --branch release/agensi-readiness https://github.com/Divithy-IT/divithy-youtube-publisher.git
cd divithy-youtube-publisher
python cli_publish.py --help
```

Confirm the help includes --upload and --approve-plan. This branch is a review
candidate, not a claim of marketplace acceptance. From that copy:

```sh
python -m venv .venv
# Linux / macOS:
.venv/bin/python -m pip install -r requirements.txt
# Windows PowerShell:
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

In the commands below, replace `python` with the path to that virtual
environment's Python. No shell activation is required.

Copy publisher_config.example.json to publisher_config.json. Set content_root,
a future start_date and timezone. Relative content_root and client_secret paths
are resolved beside the configuration file. Keep configuration, state and token
files in a private local directory. If using --config outside the repository,
state and token files default to that config's directory. Use the same state
file from every invocation for this channel. Desktop mode uses files beside
app.py, so keep its config there if using both interfaces.

Set default_language to the language of your videos. category_id defaults to 20
(Gaming); choose the appropriate category for your content. made_for_kids is an
explicit channel-owner decision. New playlists default to private; an existing
playlist keeps its current visibility. Set playlist_privacy to public only when
you want newly created playlist names and descriptions to become public.

## Prepare packages

```text
content/
  film1/
    episode.mp4
    Short_01.mp4
    Short_02.mp4
    Short_03.mp4
    Miniatura.jpg
    YouTube.txt
    gra.txt
    typ.txt
```

MP4 extensions and YouTube / Miniatura prefixes are case-sensitive. Use one
metadata file and at most one JPG/PNG thumbnail. Number the Shorts with zero
padding so alphabetical order matches their metadata. A main-only package may
omit all Shorts and their metadata sections. The thumbnail and marker files
are optional. gra.txt contains the series key, for example `Tutorials`.
typ.txt contains `kompilacja` or `pelna_rozgrywka` (or another custom type name).
Set game_order, type_order and playlist_names to match your own series.

YouTube.txt accepts English or Polish field names. Example for a main-only
package:

```text
MAIN VIDEO
Title: My first episode
Description:
Description approved by the channel owner.
Tags: tutorial, example
```

For a Shorts package append `SHORT 1`, `SHORT 2`, `SHORT 3` sections using the
same Title / Description / Tags fields. Polish `FILM GŁÓWNY`, `Tytuł`, `Opis`
and `Tagi` are also supported. Metadata files must be UTF-8.

## Preview without Google credentials

```sh
python cli_publish.py --config publisher_config.json --limit 1 --json --plan reviewed_plan.json
```

The default is always preview. It does not import the Google API client, open
OAuth or send network requests. A small local lock file coordinates access;
the plan output is private but contains unpublished metadata. Review the full
metadata, selected_keys, local and UTC dates, options and repairs. --limit only
limits NEW video uploads; supplementary repairs for known uploads are also
shown in the approved plan.

## Connect your own Google project

1. In [Google Cloud Console](https://console.cloud.google.com/), create/select a
   project and enable YouTube Data API v3.
2. Configure the OAuth consent screen and, when using Testing, add the Google
   account that manages your channel as a test user.
3. Add `https://www.googleapis.com/auth/youtube`. This permits managing playlists
   as well as videos; it is broader than an upload-only scope.
4. Create an OAuth client of type Desktop app. Download the JSON into a private
   local file and set client_secret to its path. Never put its contents, token.json
   or authorization codes into an agent conversation, a repository or Agensi.
5. Run the following command and complete Google's browser consent yourself:

```sh
python cli_publish.py --config publisher_config.json --check-channel
```

Check the returned channel title and ID against the intended channel. Set
expected_channel_id to that ID. Each channel needs its own config, state and
token; an existing upload history is bound to its channel after the first new run.
For legacy records without channel_id, first verify their existing video IDs in
YouTube Studio. This is a migration check, not proof provided by local files.

Google's current [videos.insert documentation](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert)
and [2 November 2026 revision](https://developers.google.com/youtube/data/revision_history)
say unverified projects are no longer forced to private visibility. The legacy
api_audited flag is ignored and grants no publication permission. OAuth app
verification, API compliance and quota requirements remain separate matters.
A local application using a customer's own project is not a shared verified
OAuth service supplied by this product.

## Approve an actual operation

Leave schedule_publication false for a first PRIVATE upload. To schedule public
publication, explicitly set it to true and use future dates. Past scheduled
dates are rejected because YouTube can publish those videos immediately.
Re-run the preview after every setting or asset change, including channel setup.

After the channel owner approves the displayed plan, copy its approval_sha256
into the following command, keeping the same config, state and limit:

```sh
python cli_publish.py --config publisher_config.json --limit 1 --upload --approve-plan SHA256_FROM_REVIEWED_PREVIEW
```

The program compares the approved digest with the current plan before OAuth or
uploads. The digest covers metadata, channel, privacy, notification settings,
assets' identities, selected items and supplementary repairs. It is a stale-plan
check, not an authentication token or proof of human consent. An agent must
obtain user authorization before invoking --upload; it must not approve its own
preview. Check returned video IDs and privacy/dates in YouTube Studio.

For desktop use run `python app.py` or Uruchom_publikator.bat, connect the
channel, prepare a preview, check its JSON export, then enable actual sending
and confirm. Changed settings require a fresh preview. Both interfaces share
the same publishing engine and state-file lock.

## Interrupted operations

Keep backups of config, upload_state.json and approved media in private storage.
Back up OAuth credentials separately and restrict access. Do not replace a lost
history with an empty one: reconcile already uploaded video IDs first.

The approved queue's dates are reserved at the first actual operation, even
when --limit uploads only one item. Later runs retain them; new packages append
after the reserved tail. A preview alone does not reserve dates. If dates expire,
stop and agree a replacement plan; this version does not automatically reschedule
an already reserved queue. An operator can back up the state and, after checking
YouTube Studio, remove only the relevant unuploaded entries from state.plan and
choose a future start_date. Keep all state.uploads entries. Any resulting changes
need a new preview and approval.

Completed video IDs are saved before thumbnail and playlist steps. A normal
retry repairs both steps without re-uploading that video. The program prevents
a second local process using the same state file. It does not coordinate copies
of that file on other machines.

If a video request fails or the process stops before its returned ID is saved,
state.inflight remains. The result might have succeeded at YouTube. Automatic
retry is blocked. Stop all publisher instances, back up the state, then inspect
YouTube Studio using the recorded title, filename and approximate operation time:

- If exactly one matching uploaded video exists, verify its channel, file,
  privacy and schedule. Copy state.inflight into state.uploads under its `key`,
  add the verified `video_id`, set thumbnail_set and playlist_added to false,
  and remove state.inflight. Preview again before repairing supplementary steps.
- If you have verified no upload exists after processing has settled, remove
  state.inflight only, keeping the reserved plan and upload history. Preview and
  approve again. A quota/permission error still needs this check in this version.
- If the outcome is ambiguous, keep the marker and stop. Do not guess an ID.

Changed/moved media must also be reconciled: identity uses absolute path, size
and modification time, not a full video-content hash. Keep content_root and
filenames stable. A lost state, an independent second state, or a move bypassing
these checks can still lead to duplicates; there is no distributed exactly-once
guarantee. Interrupted byte streams restart after reconciliation; this version
does not persist a resumable upload session URL across process restarts.

## Release validation

Run `python -m unittest discover -s tests -v`. Automated tests use fake API
responses; they are not a live YouTube certification. Before a paid public
launch, exercise one small private video on your own test channel, confirm its
metadata and supplementary steps, and verify one future scheduled publication.
Use a new preview for every real operation. Marketplace acceptance and its
connector delivery must be tested separately.
