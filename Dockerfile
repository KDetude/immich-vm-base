FROM --platform=linux/arm64 alpine:3.21

# ── Base system ────────────────────────────────────────────────────────────────
RUN apk update && apk add --no-cache \
    alpine-base \
    openrc \
    docker \
    docker-cli-compose \
    e2fsprogs \
    util-linux \
    linux-virt \
    busybox-extras

# ── Networking — static IP matching VZNATNetworkDeviceAttachment ───────────────
RUN printf 'auto lo\niface lo inet loopback\n\nauto eth0\niface eth0 inet static\n  address 192.168.64.2\n  netmask 255.255.255.0\n  gateway 192.168.64.1\n' \
      > /etc/network/interfaces

# ── Hostname & root password ────────────────────────────────────────────────────
RUN echo "immich-server" > /etc/hostname && \
    echo "root:root" | chpasswd

# ── OpenRC services ─────────────────────────────────────────────────────────────
RUN rc-update add docker    default 2>/dev/null || true && \
    rc-update add local     default 2>/dev/null || true && \
    rc-update add networking default 2>/dev/null || true && \
    rc-update add hostname  default 2>/dev/null || true && \
    rc-update add cgroups   default 2>/dev/null || true && \
    rc-update add devfs     sysinit 2>/dev/null || true && \
    rc-update add mdev      sysinit 2>/dev/null || true

# ── fstab ───────────────────────────────────────────────────────────────────────
RUN printf '/dev/vda\t/\text4\tdefaults,noatime\t0\t1\n' > /etc/fstab

# ── Immich directory structure ──────────────────────────────────────────────────
RUN mkdir -p /opt/immich /mnt/library /mnt/meta /data/immich/postgres

# ── Immich startup script ───────────────────────────────────────────────────────
COPY immich.start /etc/local.d/immich.start
RUN chmod +x /etc/local.d/immich.start
