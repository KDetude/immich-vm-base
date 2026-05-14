#!/usr/bin/env python3
"""Strip PE/EFI wrapper from Alpine aarch64 vmlinuz to get a raw ARM64 Image."""
import gzip, io, sys, shutil

src, dst = sys.argv[1], sys.argv[2]

with open(src, "rb") as f:
    data = f.read()

ARM64_MAGIC = b"\x41\x52\x4d\x64"

if data[56:60] == ARM64_MAGIC:
    print("Already raw ARM64 Image")
    shutil.copy(src, dst)
    sys.exit(0)

print("PE/EFI wrapper detected — extracting gzip payload…")
offset = next(
    (i for i in range(512, min(len(data) - 2, 512_000))
     if data[i:i+3] == b"\x1f\x8b\x08"),
    -1,
)
if offset < 0:
    print("ERROR: gzip magic not found in kernel binary", file=sys.stderr)
    sys.exit(1)

print(f"gzip payload at offset {offset}, decompressing…")
try:
    raw = gzip.decompress(data[offset:])
except Exception:
    with gzip.GzipFile(fileobj=io.BytesIO(data[offset:])) as gz:
        raw = gz.read()

if raw[56:60] != ARM64_MAGIC:
    print("ERROR: decompressed kernel missing ARM64 magic", file=sys.stderr)
    sys.exit(1)

with open(dst, "wb") as f:
    f.write(raw)
print(f"Extracted {len(raw):,} bytes raw ARM64 kernel → {dst}")
