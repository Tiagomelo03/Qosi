# Imagem base para os nós da topologia QoSI (Tiago Melo)
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. Ferramentas base de rede e QoS
RUN apt-get update && apt-get install -y --no-install-recommends \
        iproute2 iputils-ping net-tools ethtool tcpdump procps \
        nftables iptables \
        iperf3 netcat-openbsd curl \
        python3 python3-pip python3-scapy \
    && rm -rf /var/lib/apt/lists/*

# 2. D-ITG para simulação realista de VoIP (G.711)
RUN apt-get update \
    && (apt-get install -y --no-install-recommends d-itg \
        || echo "AVISO: d-itg indisponível, fallback para iperf3") \
    && rm -rf /var/lib/apt/lists/*

# 3. NFQUEUE para a VNF de Classificação (Python Scapy intercetar tráfego na Fase 2)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libnetfilter-queue-dev build-essential python3-dev \
    && pip3 install --no-cache-dir NetfilterQueue \
    && apt-get purge -y build-essential python3-dev \
    && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Correção obrigatória para manter os contentores vivos no WSL 2 / Containernet
CMD ["/bin/bash"]