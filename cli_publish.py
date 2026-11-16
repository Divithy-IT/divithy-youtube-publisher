"""Preview locally; upload only the plan explicitly approved by the user."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from local_state import load_state, state_lock, write_private
from publishing import load_config, prepare, publish

APP_DIR = Path(__file__).resolve().parent


def main(argv=None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=APP_DIR / "publisher_config.json")
    parser.add_argument("--state", type=Path, help="Default: upload_state.json beside config")
    parser.add_argument("--token", type=Path, help="Default: token.json beside config")
    parser.add_argument("--plan", type=Path, help="Write a private JSON preview to this path")
    parser.add_argument("--limit", type=int, default=0, help="Maximum new uploads; 0 means all")
    parser.add_argument("--inspect-only", action="store_true", help="Preview (also the default)")
    parser.add_argument("--json", action="store_true", help="Print the full plan as JSON")
    parser.add_argument("--upload", action="store_true", help="Perform the explicitly approved plan")
    parser.add_argument("--approve-plan", help="SHA-256 from the reviewed preview")
    parser.add_argument("--check-channel", action="store_true", help="Authorize and read channel ID; no uploads")
    args = parser.parse_args(argv)
    if args.limit < 0:
        parser.error("--limit must be zero or positive")
    if args.upload and (args.inspect_only or args.check_channel):
        parser.error("--upload cannot be combined with --inspect-only or --check-channel")
    if args.upload and not args.approve_plan:
        parser.error("--upload requires --approve-plan from a reviewed preview")
    if args.approve_plan and not args.upload:
        parser.error("--approve-plan requires --upload")
    config_path = args.config.expanduser().resolve()
    state_path = (args.state or config_path.parent / "upload_state.json").resolve()
    token_path = (args.token or config_path.parent / "token.json").resolve()
    protected = {state_path, token_path, config_path}
    if len(protected) != 3 or (args.plan and args.plan.resolve() in protected):
        parser.error("Config, state, token and plan must use different files")
    try:
        config = load_config(config_path)
        secret = Path(config["client_secret"])
        if secret in protected or (args.plan and args.plan.resolve() == secret):
            parser.error("OAuth credentials must use a separate file")
        with state_lock(state_path):
            if args.check_channel:
                from youtube_api import authenticate, connected_channel
                youtube = authenticate(secret, token_path)
                print(json.dumps(connected_channel(youtube), ensure_ascii=False))
                return
            state = load_state(state_path)
            items, plan, digest = prepare(config, state, args.limit)
            if args.upload and digest != args.approve_plan:
                parser.error("Plan or settings changed. Preview and approve the new SHA-256 first.")
            if args.plan:
                write_private(args.plan, json.dumps(plan, ensure_ascii=False, indent=2))
            if args.json:
                print(json.dumps(plan, ensure_ascii=False, indent=2))
            else:
                selected = set(plan["selected_keys"])
                for item in items:
                    label = "UPLOAD" if item.key in selected else "SAVED / NOT SELECTED"
                    print(label, item.publish_at.isoformat(), item.video.name, item.metadata.title)
                mode = "scheduled publication" if plan["options"]["schedule_publication"] else "PRIVATE ONLY"
                print(f"Mode: {mode}; new uploads: {plan['new_upload_count']}; repairs: {len(plan['repairs'])}")
                print(f"Approval SHA-256: {digest}")
            if not args.upload:
                return
            if not plan["new_upload_count"] and not plan["repairs"]:
                print("Nothing to upload or repair.")
                return
            if not plan["options"]["expected_channel_id"]:
                parser.error("Set expected_channel_id using --check-channel before uploading")
            from youtube_api import authenticate
            youtube = authenticate(secret, token_path)
            publish(youtube, config, state, state_path, items, plan)
            print("Finished. Verify video IDs, privacy and dates in YouTube Studio.")
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, f"Publisher: {error}\n")


if __name__ == "__main__":
    main()
