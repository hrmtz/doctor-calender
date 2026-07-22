#!/usr/bin/env python3
"""drive_upload.py — 生成PNGを共有ドライブの月フォルダへアップロードする。

SA(seo-research) がメンバーの Shared Drive にのみ書ける(SAは個人枠なし)。
find-or-create でフォルダ/ファイルを冪等更新。
Usage: drive_upload.py <drive_id> <month_label> <png_dir> [sa_key]
"""
import os
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

FOLDER_MIME = "application/vnd.google-apps.folder"


def _svc(key):
    creds = service_account.Credentials.from_service_account_file(
        key, scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def find_or_create_folder(svc, drive_id, parent, name):
    q = (f"name='{name}' and mimeType='{FOLDER_MIME}' and "
         f"'{parent}' in parents and trashed=false")
    res = svc.files().list(q=q, corpora="drive", driveId=drive_id,
                           includeItemsFromAllDrives=True, supportsAllDrives=True,
                           fields="files(id,name)").execute().get("files", [])
    if res:
        return res[0]["id"]
    meta = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent]}
    return svc.files().create(body=meta, supportsAllDrives=True, fields="id").execute()["id"]


def upload_file(svc, folder, path):
    name = os.path.basename(path)
    media = MediaFileUpload(path, mimetype="image/png", resumable=True)
    q = f"name='{name}' and '{folder}' in parents and trashed=false"
    ex = svc.files().list(q=q, includeItemsFromAllDrives=True, supportsAllDrives=True,
                          fields="files(id)").execute().get("files", [])
    if ex:
        svc.files().update(fileId=ex[0]["id"], media_body=media,
                           supportsAllDrives=True, fields="id").execute()
        return "updated"
    svc.files().create(body={"name": name, "parents": [folder]}, media_body=media,
                       supportsAllDrives=True, fields="id").execute()
    return "created"


def main():
    drive_id, month_label, png_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    key = sys.argv[4] if len(sys.argv) > 4 else \
        "/home/hrmtz/projects/seo-research/secrets/service_account.json"
    svc = _svc(key)
    folder = find_or_create_folder(svc, drive_id, drive_id, month_label)
    pngs = sorted(f for f in os.listdir(png_dir) if f.endswith(".png"))
    for i, f in enumerate(pngs, 1):
        st = upload_file(svc, folder, os.path.join(png_dir, f))
        print(f"  [{i}/{len(pngs)}] {st}  {f}")
    print(f"DONE {len(pngs)} files -> Shared Drive / {month_label}/  (folderId={folder})")


if __name__ == "__main__":
    main()
