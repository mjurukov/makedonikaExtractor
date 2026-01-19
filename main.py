import requests
from urllib.parse import quote, urljoin
import re
import zipfile
import os
import shutil

print("Преземање на книга од makedonika.mk во EPUB формат")
print("--------------------------------------------------\n")

ime_kniga = input("Внесете име на книга (на кирилица): ").strip()
id_kniga = input("Внесете ID на книга (на пример 3262): ").strip()
ime_epub = input("Име на EPUB датотеката (без .epub): ").strip()

if not ime_kniga or not id_kniga or not ime_epub:
    print("Мора да ги внесете сите три полиња.")
    exit()

folder_raw = ime_kniga + id_kniga
folder = quote(folder_raw)

base_url = f"http://www.makedonika.mk/Upload/EpubExtract/{folder}/OEBPS/"

temp_folder = "temp_epub"

os.makedirs(f"{temp_folder}/META-INF", exist_ok=True)
os.makedirs(f"{temp_folder}/Text", exist_ok=True)
os.makedirs(f"{temp_folder}/Images", exist_ok=True)

with open(f"{temp_folder}/mimetype", "w", encoding="ascii") as f:
    f.write("application/epub+zip")

with open(f"{temp_folder}/META-INF/container.xml", "w", encoding="utf-8") as f:
    f.write('''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>''')

print(f"\nСе обидуваме да ја преземеме книгата: {ime_kniga}{id_kniga}")
print(f"URL: {base_url}\n")

opf_url = urljoin(base_url, "content.opf")
r = requests.get(opf_url)

if r.status_code != 200:
    print("Грешка: content.opf не е пронајден.")
    print("Можеби погрешно име или ID на книга?")
    exit()

with open(f"{temp_folder}/content.opf", "wb") as f:
    f.write(r.content)

print("✓ Преземен content.opf")

chapters = sorted(re.findall(r'href="([^"]+\.xhtml)"', r.text))

if not chapters:
    print("Не се пронајдени поглавја во content.opf.")
    exit()

print(f"Пронајдени се {len(chapters)} поглавја\n")

for href in chapters:
    chapter_url = urljoin(base_url, href)
    local_path = f"{temp_folder}/{href}"

    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    r = requests.get(chapter_url)
    if r.ok:
        with open(local_path, "wb") as f:
            f.write(r.content)
        print(f"✓ {href}")
    else:
        print(f"✗ Не успеа: {href}")

# (опционално) toc.ncx ако постои
toc_url = urljoin(base_url, "toc.ncx")
r = requests.get(toc_url)
if r.ok:
    with open(f"{temp_folder}/toc.ncx", "wb") as f:
        f.write(r.content)
    print("✓ toc.ncx")

epub_ime = f"{ime_epub}.epub"

with zipfile.ZipFile(epub_ime, "w", zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(
        f"{temp_folder}/mimetype",
        "mimetype",
        compress_type=zipfile.ZIP_STORED
    )

    for root_dir, _, files in os.walk(temp_folder):
        for file in files:
            full_path = os.path.join(root_dir, file)
            arcname = os.path.relpath(full_path, temp_folder).replace("\\", "/")
            if arcname != "mimetype":
                zipf.write(full_path, arcname)

print(f"\nГотово!")
print(f"Книгата е зачувана како: {epub_ime}")

shutil.rmtree(temp_folder, ignore_errors=True)