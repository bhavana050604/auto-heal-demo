#!/usr/bin/env python3
import argparse, sqlite3, json, os, subprocess
def run(cmd):
    print('>', ' '.join(cmd)); return subprocess.run(cmd, check=True)
def ensure_db(dbpath):
    os.makedirs(os.path.dirname(dbpath), exist_ok=True)
    conn = sqlite3.connect(dbpath)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signature TEXT,
        action_type TEXT,
        action_payload TEXT,
        hit_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    return conn
def add_mapping(conn, signature, file, search, replace):
    cur = conn.cursor()
    payload = {'file': file, 'search': search, 'replace': replace}
    cur.execute("INSERT INTO mappings (signature, action_type, action_payload) VALUES (?, ?, ?)",
                (signature, "patch_replace", json.dumps(payload)))
    conn.commit()
    return cur.lastrowid
def commit_db(dbpath, message="Add healer mapping"):
    run(["git", "add", dbpath])
    try:
        run(["git", "commit", "-m", message])
    except subprocess.CalledProcessError:
        print("Nothing to commit or commit failed.")
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signature", required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--search", required=True)
    ap.add_argument("--replace", required=True)
    ap.add_argument("--db", default="healer/db.sqlite")
    args = ap.parse_args()
    conn = ensure_db(args.db)
    rid = add_mapping(conn, args.signature, args.file, args.search, args.replace)
    print("Inserted mapping id", rid)
    print("Committing db to repository (you can push to remote):")
    commit_db(args.db, message=f"Add healer mapping id {rid}")
if __name__ == '__main__':
    main()
