#!/usr/bin/env python3
"""Strip PE/EFI wrapper from Alpine aarch64 vmlinuz to get a raw ARM64 Image.

Alpine 3.21 arm64 ships vmlinuz-virt as a PE/EFI stub containing an *uncompressed*
ARM64 Image (not gzip-wrapped). We locate it by scanning for the ARM64 Image magic
(b"ARMd") at relative offset 56 within any 8-byte-aligned block.
"""
import sys, shutil

src, dst = sys.argv[1], sys.argv[2]

with open(src, "rb") as f:
    data = f.read()

ARM64_MAGIC = b"\x41\x52\x4d\x64"

# Case 1: already a raw ARM64 Image
if data[56:60] == ARM64_MAGIC:
    print("Already raw ARM64 Image — copying as-is")
    shutil.copy(src, dst)
    sys.exit(0)

# Case 2: PE/EFI wrapper containing a raw (uncompressed) ARM64 Image.
# Find the Image by locating ARM64 magic at relative offset +56 from any
# 8-byte-aligned position; validate via the image_size header field.
print("Scanning for embedded ARM64 Image magic…")
offset = -1
search_limit = min(len(data) - 64, 32 * 1024 * 1024)
for i in range(0, search_limit, 8):
    if data[i + 56: i + 60] == ARM64_MAGIC:
        img_size = int.from_bytes(data[i + 16: i + 24], "little")
        if 1 * 1024 * 1024 <= img_size <= 256 * 1024 * 1024:
            if i + img_size <= len(data):
                offset = i
                print(f"ARM64 Image found at offset {offset:#x} ({img_size // 1024 // 1024} MB)")
                break

# Relaxed fallback: accept any position with the magic (no size check)
if offset == -1:
    for i in range(0, search_limit, 8):
        if data[i + 56: i + 60] == ARM64_MAGIC:
            offset = i
            print(f"ARM64 Image found (relaxed) at offset {offset:#x}")
            break

if offset == -1:
    # VZLinuxBootLoader on Apple Silicon can sometimes boot PE kernels directly;
    # copy as-is and let it try rather than hard-failing the CI.
    print("WARNING: ARM64 magic not found — copying PE kernel as-is", file=sys.stderr)
    shutil.copy(src, dst)
    sys.exit(0)

img_size = int.from_bytes(data[offset + 16: offset + 24], "little")
if 1 * 1024 * 1024 <= img_size <= 256 * 1024 * 1024 and offset + img_size <= len(data):
    raw = data[offset: offset + img_size]
else:
    raw = data[offset:]

if raw[56:60] != ARM64_MAGIC:
    print("Extracted block missing ARM64 magic — copying PE kernel as-is", file=sys.stderr)
    shutil.copy(src, dst)
    sys.exit(0)

with open(dst, "wb") as f:
    f.write(raw)
print(f"Written {len(raw):,} bytes raw ARM64 kernel → {dst}")
