#!/usr/bin/env python3
"""Strip PE/EFI wrapper from Alpine aarch64 vmlinuz to get a raw ARM64 Image.

Alpine arm64 vmlinuz-virt uses a "zimg" PE format:
  offset 0-1 : "MZ"  (DOS/PE magic)
  offset 4-7 : "zimg" (Alpine zImage marker)
  offset 8-11: gzip payload offset (little-endian u32)
  offset 12-15: gzip payload size  (little-endian u32)

Python 3.12 gzip.decompress() fails on trailing data after the first member.
We use zlib.decompressobj(wbits=47) which stops cleanly at stream end.
"""
import sys, struct, zlib, shutil

src, dst = sys.argv[1], sys.argv[2]

with open(src, "rb") as f:
    data = f.read()

ARM64_MAGIC = b"\x41\x52\x4d\x64"

# Case 1: already a raw ARM64 Image
if data[56:60] == ARM64_MAGIC:
    print("Already raw ARM64 Image — copying as-is")
    shutil.copy(src, dst)
    sys.exit(0)

# Case 2: Alpine "zimg" PE wrapper
# Header: MZ + "zimg" + gzip_offset (u32 LE) + gzip_size (u32 LE)
if data[4:8] == b"zimg":
    gzip_off  = struct.unpack_from("<I", data,  8)[0]
    gzip_size = struct.unpack_from("<I", data, 12)[0]
    print(f"zimg PE wrapper: gzip payload at {gzip_off:#x} ({gzip_size // 1024} KB)")

    payload = data[gzip_off : gzip_off + gzip_size] if gzip_size else data[gzip_off:]

    # zlib.decompressobj stops at end of first gzip member — no trailing-data error
    try:
        d = zlib.decompressobj(wbits=47)   # 47 = 15+32 = gzip auto-detect
        raw = d.decompress(payload, 512 * 1024 * 1024)
    except zlib.error as e:
        print(f"ERROR: zlib decompress failed: {e}", file=sys.stderr)
        sys.exit(1)

    if raw[56:60] != ARM64_MAGIC:
        print(f"ERROR: decompressed kernel missing ARM64 magic ({raw[56:60].hex()})",
              file=sys.stderr)
        sys.exit(1)

    with open(dst, "wb") as f:
        f.write(raw)
    print(f"Extracted {len(raw):,} bytes raw ARM64 kernel -> {dst}")
    sys.exit(0)

# Case 3: raw ARM64 Image embedded in PE — scan for magic at relative offset 56
print("Scanning for embedded ARM64 Image magic...")
offset = -1
for i in range(0, min(len(data) - 64, 32 * 1024 * 1024), 8):
    if data[i + 56 : i + 60] == ARM64_MAGIC:
        img_sz = int.from_bytes(data[i + 16 : i + 24], "little")
        if 1 * 1024 * 1024 <= img_sz <= 256 * 1024 * 1024 <= len(data) - i:
            offset = i
            print(f"ARM64 Image found at offset {offset:#x} ({img_sz // 1024 // 1024} MB)")
            break

if offset >= 0:
    img_sz = int.from_bytes(data[offset + 16 : offset + 24], "little")
    raw = data[offset : offset + img_sz]
    with open(dst, "wb") as f:
        f.write(raw)
    print(f"Written {len(raw):,} bytes -> {dst}")
    sys.exit(0)

# Fallback: copy PE as-is (VZLinuxBootLoader on Apple Silicon accepts PE kernels)
print("WARNING: falling back to PE kernel as-is", file=sys.stderr)
shutil.copy(src, dst)
sys.exit(0)
