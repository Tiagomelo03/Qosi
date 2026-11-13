# TP3 QoSI — Implementação de Mecanismos de QoS com VNFs em Containernet

Este repositório contém a implementação do Trabalho Prático 3 (QoSI), simulando uma topologia de rede ISP baseada em Service Function Chaining (SFC) com Containernet (Docker + Mininet).

---

## 🏗️ Arquitetura da Rede e Cadeia SFC

O caminho de dados implementa uma cadeia de Funções de Rede Virtualizadas (SFC) estruturada da seguinte forma:

$$\text{LAN Clientes } (\text{s1}) \longrightarrow \texttt{vnf\_cls} \longrightarrow \texttt{vnf\_acl} \longrightarrow \texttt{vnf\_qos} \longrightarrow \texttt{r\_isp} \longrightarrow \texttt{r\_core} \longrightarrow \text{LAN Servidores } (\text{s2})$$

* **Rede de Clientes (`s1`):** Sub-rede `172.20.10.0/24` (inclui nós de VoIP, Vídeo, Dados e Tráfego Indesejado).
* **Cadeia SFC:**
  * `vnf_cls`: Classificação e marcação de pacotes (DSCP).
  * `vnf_acl`: Controlo de acesso (Firewall / nftables).
  * `vnf_qos`: Controlo de tráfego, policiamento e agendamento de filas.
* **Rede de Transporte e Borda (`r_isp` & `r_core`):** Aplicação de gargalo de acesso ($10\text{ Mbit/s}$) e atraso WAN ($10\text{ ms}$).
* **Rede de Servidores (`s2`):** Sub-rede `172.20.20.0/24` (Data Center).
* **Rede de Gestão Out-of-Band (`s3`):** Sub-rede `192.168.99.0/24` para a sonda de monitorização (`vnf_mon`).

---

## ⚙️ Requisitos do Sistema

* **Ambiente Recomendado:** Ubuntu 22.04 LTS (nativo ou via WSL 2 com integração Docker direta).
* **Dependências:** Python 3, Docker, Open vSwitch e Containernet.

---

## 🚀 Guia de Instalação e Execução para o Grupo

Siga estes passos no seu terminal para colocar o ambiente a funcionar rapidamente:

### 1. Clonar o Repositório e Criar o Ambiente Virtual
Recomenda-se isolar o ambiente Python para evitar conflitos com pacotes globais do sistema:
```bash
git clone <url-do-repositorio>
cd TP3
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### 2. Instalar o Containernet (caso ainda não o tenha)
Se o Containernet não estiver configurado na máquina, execute o instalador oficial de referência:
```bash
git clone https://github.com/containernet/containernet.git ~/containernet
sudo ansible-playbook -i "localhost," -c local ~/containernet/ansible/install.yml
cd ~/containernet && pip install .
cd -
```

### 3. Construir a Imagem Docker das VNFs
Construa a imagem base utilizada pelos contentores da topologia:
```bash
./build_image.sh
```

---

## 🧪 Testes e Validação (Fase 1)

### Teste Rápido de Conectividade
Para validar se todos os nós comunicam corretamente e se as tabelas de encaminhamento estão ativas:
```bash
sudo -E env PATH="$PATH" VIRTUAL_ENV="$VIRTUAL_ENV" python3 topologia_isp.py --test
```
*(Deverá obter uma taxa de sucesso de 100% nos pings entre clientes, servidores e na rede de gestão).*

### Executar a Topologia Interativa
Para abrir a linha de comandos do Mininet (útil para testes manuais e depuração):
```bash
sudo -E env PATH="$PATH" VIRTUAL_ENV="$VIRTUAL_ENV" python3 topologia_isp.py
```

### Simulação de Tráfego Concorrente (Fase 1)
Com a topologia em execução, pode disparar os perfis de tráfego (VoIP, Vídeo e Best-Effort) em paralelo sobre o nosso gargalo de $10\text{ Mbit/s}$:
```bash
sudo ./trafego/gerar_cenarios.sh 20
```
Os relatórios detalhados em formato JSON serão guardados automaticamente na pasta `resultados_fase1/`.

---

## 👥 Elementos do Grupo
* **Tiago Melo**
* **Gonçalo Soares**
* **Nádia Freitas**