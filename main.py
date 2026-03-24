import argparse
import os
import re
import shutil
import sys
import zipfile
from urllib.parse import quote, urljoin

import requests

SITE = "http://www.makedonika.mk"
POPUP_URL = f"{SITE}/Kniga_popup_knigoteka.aspx?idBook={{id}}"
EPUB_BASE = f"{SITE}/Upload/EpubExtract/{{folder}}/OEBPS/"

CONTAINER_XML = (
    '<?xml version="1.0"?>'
    '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
    "<rootfiles>"
    '<rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>'
    "</rootfiles>"
    "</container>"
)


def fetch_title(book_id: str) -> str:
    url = POPUP_URL.format(id=book_id)
    r = requests.get(url, timeout=15)
    r.raise_for_status()

    m = re.search(r'(?:naslov_kn|lblNaslov)[^>]*>([^<]+)<', r.text)
    if m:
        return m.group(1).strip()

    m = re.search(r'>([^<]{2,}?)\s*Автор:', r.text)
    if m:
        return m.group(1).strip()

    raise ValueError(f"Could not extract title for book {book_id}: {url}")


def download_file(url: str, dest: str) -> bool:
    try:
        r = requests.get(url, timeout=30)
        if r.ok:
            os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
            with open(dest, "wb") as f:
                f.write(r.content)
            return True
    except requests.RequestException:
        pass
    return False


def build_epub(book_id: str, output_path: str | None = None) -> str:
    print(f"Fetching metadata for book {book_id}...")
    title = fetch_title(book_id)
    print(f"  Title: {title}")

    folder_encoded = quote(title + book_id)
    base_url = EPUB_BASE.format(folder=folder_encoded)

    temp = f"_temp_epub_{book_id}"
    shutil.rmtree(temp, ignore_errors=True)
    os.makedirs(f"{temp}/META-INF", exist_ok=True)

    with open(f"{temp}/mimetype", "w", encoding="ascii") as f:
        f.write("application/epub+zip")
    with open(f"{temp}/META-INF/container.xml", "w", encoding="utf-8") as f:
        f.write(CONTAINER_XML)

    opf_url = urljoin(base_url, "content.opf")
    r = requests.get(opf_url, timeout=15)
    if r.status_code != 200:
        shutil.rmtree(temp, ignore_errors=True)
        raise FileNotFoundError(f"content.opf not found at {opf_url}")

    with open(f"{temp}/content.opf", "wb") as f:
        f.write(r.content)

    hrefs = sorted(set(
        re.findall(r'href="([^"]+)"', r.text)
        + re.findall(r'src="([^"]+)"', r.text)
    ))

    if not hrefs:
        shutil.rmtree(temp, ignore_errors=True)
        raise ValueError("No files referenced in content.opf")

    print(f"  Downloading {len(hrefs)} files...")
    ok, fail = 0, 0
    for href in hrefs:
        file_url = urljoin(base_url, href)
        local_path = os.path.join(temp, href)
        if download_file(file_url, local_path):
            ok += 1
        else:
            fail += 1
            print(f"  WARN: failed to download {href}")

    if not any(h.endswith("toc.ncx") for h in hrefs):
        download_file(urljoin(base_url, "toc.ncx"), f"{temp}/toc.ncx")

    if output_path is None:
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", title)
        output_path = f"{safe_name}.epub"
    if not output_path.endswith(".epub"):
        output_path += ".epub"

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(f"{temp}/mimetype", "mimetype", compress_type=zipfile.ZIP_STORED)
        for root_dir, _, files in os.walk(temp):
            for fname in files:
                full = os.path.join(root_dir, fname)
                arcname = os.path.relpath(full, temp).replace("\\", "/")
                if arcname != "mimetype":
                    zf.write(full, arcname)

    shutil.rmtree(temp, ignore_errors=True)
    print(f"  Saved: {output_path} ({ok} files, {fail} failed)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Download books from makedonika.mk as EPUB")
    parser.add_argument("book_id", help="Book ID from the site URL (e.g. 15337)")
    parser.add_argument("-o", "--output", help="Output filename", default=None)
    args = parser.parse_args()

    try:
        build_epub(args.book_id, args.output)
    except (FileNotFoundError, ValueError, requests.RequestException) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
