# makedonika-epub

Download books from [makedonika.mk](http://www.makedonika.mk) as EPUB files.

## Setup

```
pip install requests
```

## Usage

Find the book ID from the site URL (e.g. `idBook=15337`) and run:

```
python makedonika_epub.py 15337
```

The output file is named after the book title automatically. To specify a custom filename:

```
python makedonika_epub.py 15337 -o betoven.epub
```

## How it works

1. Fetches the book's metadata page to extract the title
2. Downloads all EPUB assets (chapters, stylesheets, images, fonts) from the server
3. Packages them into a valid `.epub` file
