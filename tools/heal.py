#!/usr/bin/env python3
"""heal.py
- Usage: python3 tools/heal.py --log logs/test.log --db healer/db.sqlite
"""
import argparse, sqlite3, re, json, subprocess, sys, os, requests

def run(cmd, check=True, capture=False):
    print(">", " ".join(cmd))
    if capture:
        return subprocess.check_output(cmd, text=True)
    else:
        return subprocess.run(cmd, check=check)

def find_signature_in_log(log_text, conn):
    cur = conn.cursor()
    cur.execute("SELECT id, signature, action_type, action_payload FROM mappings")
    rows = cur.fetchall()
    for rid, signature, action_type, action_payload in rows:
        try:
            if re.search(signature, log_text, re.MULTILINE):
                return {'id': rid, 'signature': signature, 'action_type': action_type, 'action_payload': json.loads(action_payload)}
        except re.error:
            if signature in log_text:
                return {'id': rid, 'signature': signature, 'action_type': action_type, 'action_payload': json.loads(action_payload)}
    return None

def apply_patch_replace(payload):
    fpath = payload.get("file")
    search = payload.get("search")
    replace = payload.get("replace")
    if not (fpath and (search is not None) and (replace is not None)):
        raise ValueError("Invalid payload for patch_replace")
    if not os.path.exists(fpath):
        raise FileNotFoundError(f"{fpath} not found")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    if search not in content:
        print("Search text not found in file. Aborting patch.")
        return False
    content = content.replace(search, replace, 1)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Applied replace in {fpath}")
    return True

def commit_and_push(message):
    run(["git", "config", "user.email", "auto-heal@example.com"])
    run(["git", "config", "user.name", "auto-heal-bot"])
    run(["git", "add", "-A"])
    try:
        run(["git", "commit", "-m", message])
    except subprocess.CalledProcessError:
        print("Nothing to commit.")
        return False
    run(["git", "push"])
    return True

def create_github_issue(repo, token, title, body):
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    data = {"title": title, "body": body}
    resp = requests.post(url, headers=headers, json=data, timeout=15)
    print("GitHub issue creation status:", resp.status_code)
    if resp.status_code not in (200,201):
        print("Issue response:", resp.text)
    else:
        print("Created issue:", resp.json().get("html_url"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    args = ap.parse_args()

    if not os.path.exists(args.log):
        print("Log file not found:", args.log); sys.exit(0)
    with open(args.log, "r", encoding="utf-8", errors="ignore") as f:
        log_text = f.read()
    if not os.path.exists(args.db):
        print("DB not found:", args.db); sys.exit(0)
    conn = sqlite3.connect(args.db)
    mapping = find_signature_in_log(log_text, conn)
    if mapping:
        print("Found matching mapping:", mapping['signature'])
        payload = mapping['action_payload']
        applied = False
        if mapping['action_type'] == "patch_replace":
            try:
                applied = apply_patch_replace(payload)
            except Exception as e:
                print("Error applying patch:", e); applied = False
        else:
            print("Unknown action_type:", mapping['action_type'])
        if applied:
            cur = conn.cursor()
            cur.execute("UPDATE mappings SET hit_count = hit_count + 1 WHERE id = ?", (mapping['id'],))
            conn.commit()
            msg = f"Auto-heal: applied fix for signature '{mapping['signature']}'"
            ok = commit_and_push(msg)
            if ok:
                print("Committed and pushed fix. A new workflow run will be triggered by the push.")
                sys.exit(0)
            else:
                print("Applied patch but could not push."); sys.exit(1)
        else:
            print("Mapping found but patch not applied."); sys.exit(1)
    else:
        print("No mapping matched the log.")
        if args.token and args.repo:
            title = "[Auto-Heal] Unrecognized failure - please investigate"
            snippet = "\n".join(log_text.splitlines()[-80:])
            body = f"An automated run failed and no mapping matched.\n\nLast part of log:\n```\n{snippet}\n```\nYou can teach the system by running `tools/teach.py` to add a mapping."
            try:
                create_github_issue(args.repo, args.token, title, body)
            except Exception as e:
                print("Failed to create GitHub issue:", e)
        else:
            print("No token/repo to create issue.")
        sys.exit(1)

if __name__ == '__main__':
    main()
