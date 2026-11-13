#!/usr/bin/env bash
# Script para gerar os 3 perfis de tráfego da Fase 1 (VoIP, Vídeo e Dados Best-Effort)
# Uso: sudo ./trafego/gerar_cenarios.sh [duracao_segundos]

DURACAO=${1:-20}
mkdir -p resultados_fase1

echo "[*] A iniciar servidores iperf3 na LAN do Data Center..."
sudo docker exec -d mn.s_voip iperf3 -s -p 5004
sudo docker exec -d mn.s_video iperf3 -s -p 5005
sudo docker exec -d mn.s_data iperf3 -s -p 5006
sleep 1

echo "[*] A disparar cenários concorrentes durante ${DURACAO}s (Bottleneck = 10 Mbit/s)..."

# 1. Tráfego VoIP (UDP, pacotes pequenos de 160 bytes a 100 Kbps - G.711)
echo "  -> [VoIP]   c_voip  -> s_voip:5004  (UDP 100 Kbit/s, payload 160B)"
sudo docker exec mn.c_voip iperf3 -c 172.20.20.11 -p 5004 -u -b 100K -l 160 -t "$DURACAO" -J > resultados_fase1/voip_baseline.json &
PID_VOIP=$!

# 2. Tráfego de Streaming de Vídeo (UDP constante a 6 Mbit/s, payload 1200B)
echo "  -> [Vídeo] c_video -> s_video:5005 (UDP 6 Mbit/s, payload 1200B)"
sudo docker exec mn.c_video iperf3 -c 172.20.20.12 -p 5005 -u -b 6M -l 1200 -t "$DURACAO" -J > resultados_fase1/video_baseline.json &
PID_VIDEO=$!

# 3. Tráfego de Dados em Massa / Best-Effort (TCP ganancioso com 4 fluxos paralelos)
echo "  -> [Bulk]   c_data  -> s_data:5006  (TCP 4 streams paralelas - Best Effort)"
sudo docker exec mn.c_data iperf3 -c 172.20.20.13 -p 5006 -P 4 -t "$DURACAO" -J > resultados_fase1/data_baseline.json &
PID_DATA=$!

wait $PID_VOIP $PID_VIDEO $PID_DATA
echo "[+] Testes concluídos! Resultados JSON guardados na pasta './resultados_fase1/'."