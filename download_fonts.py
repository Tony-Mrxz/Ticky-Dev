import urllib.request, ssl, os, zipfile, io

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Accept": "*/*",
}

FONTS_DIR = os.path.join(os.path.dirname(__file__), "styles", "fonts")

def dl(url, dest_name):
    dest = os.path.join(FONTS_DIR, dest_name)
    if os.path.exists(dest):
        print(f"  [SKIP] {dest_name}")
        return True
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            data = r.read()
        # Validate it's a TTF or OTF
        magic = data[:4]
        valid = magic in [b'\x00\x01\x00\x00', b'OTTO', b'true', b'typ1', b'wOFF', b'wOF2']
        if not valid:
            print(f"  [WARN] {dest_name}: not a font file (magic={magic}), got {len(data)} bytes")
            return False
        with open(dest, "wb") as f:
            f.write(data)
        print(f"  [OK]   {dest_name} ({len(data)//1024}KB)")
        return True
    except Exception as e:
        print(f"  [FAIL] {dest_name}: {e}")
        return False

# Direct GitHub release / raw links
attempts = [
    # Manrope — check the latest tag
    ("Manrope-Regular.ttf",    "https://github.com/sharanda/manrope/raw/master/fonts/ttf/Manrope-ExtraLight.ttf"),
    ("Manrope-Regular.ttf",    "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/Manrope%5Bwght%5D.ttf"),
    # Outfit
    ("Outfit-Regular.ttf",     "https://raw.githubusercontent.com/google/fonts/main/ofl/outfit/Outfit%5Bwght%5D.ttf"),
    # IBM Plex Sans
    ("IBMPlexSans-Regular.ttf","https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexsans/IBMPlexSans-Regular.ttf"),
    # Geist (Vercel releases their fonts as individual TTFs in GitHub releases)
    ("Geist-Regular.ttf",      "https://github.com/vercel/geist-font/raw/main/packages/next/src/fonts/geist-sans/Geist-Regular.woff2"),
    # Fallback for Geist using NPM package raw
    ("Geist-Regular.ttf",      "https://unpkg.com/geist@1.3.0/dist/fonts/geist-sans/Geist-Regular.woff2"),
]

done = set()
for fname, url in attempts:
    if fname in done:
        continue
    if os.path.exists(os.path.join(FONTS_DIR, fname)):
        print(f"  [SKIP] {fname}")
        done.add(fname)
        continue
    if dl(url, fname):
        done.add(fname)

print("\nFonts directory:")
for f in sorted(os.listdir(FONTS_DIR)):
    sz = os.path.getsize(os.path.join(FONTS_DIR, f))
    print(f"  {f:50s} {sz//1024}KB")
