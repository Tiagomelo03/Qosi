#!/usr/bin/env bash
set -e
echo "[*] A construir a imagem Docker qosi/vnf-node:latest..."
sudo docker build -t qosi/vnf-node:latest .
echo "[+] Imagem criada com sucesso!"