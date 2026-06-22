#!/bin/bash
# Procedura zarządzania Lumina (Node 1) via VAIO (Tailscale)
# Hasło vaio: mwzmjsunp
# Skrypt automatycznie budzi komputer i wyłącza monitory.

echo "Connecting to VAIO to wake Lumina (Grzegorz Mode)..."
sshpass -p "mwzmjsunp" ssh -o StrictHostKeyChecking=no root@100.117.242.21 "/root/Skrypty/lumina_grzegorz"

