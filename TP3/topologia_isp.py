#!/usr/bin/env python3
"""
TP3 QoSI — Topologia tipo ISP em Containernet (Autor: Tiago Melo)

Cadeia SFC:
  LAN Clientes (s1) -> vnf_cls -> vnf_acl -> vnf_qos =[10 Mbit/s]=> r_isp =[núcleo]=> r_core -> LAN servidores (s2)
                         \\_________\\_________\\____ rede de gestão (s3) ____ vnf_mon

Nota: o Containernet atribui por defeito um IP 10.0.0.x/8 à primeira interface de
cada nó. Por isso todos os IPs são definidos explicitamente em configure()
(flush + add), antes das rotas.
"""
import argparse
import os
import subprocess
import sys

from mininet.net import Containernet
from mininet.node import OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error

REPO = os.path.dirname(os.path.abspath(__file__))
IMG = 'qosi/vnf-node:latest'

# --------------------------------------------------------------------------- #
# Plano de endereçamento
# --------------------------------------------------------------------------- #
CLIENTES = {
    'c_voip':   '172.20.10.11',
    'c_video':  '172.20.10.12',
    'c_data':   '172.20.10.13',
    'c_hacker': '172.20.10.99',
}
SERVIDORES = {
    's_voip':   '172.20.20.11',
    's_video':  '172.20.20.12',
    's_data':   '172.20.20.13',
}
GESTAO = {
    'vnf_cls':  '192.168.99.2',
    'vnf_acl':  '192.168.99.3',
    'vnf_qos':  '192.168.99.4',
    'vnf_mon':  '192.168.99.100',
}

# IPs de todas as interfaces das VNFs e routers (interface -> CIDR)
IPS = {
    'vnf_cls': {'c-in': '172.20.10.1/24', 'c-out': '10.100.1.1/30', 'cls-mgmt': '192.168.99.2/24'},
    'vnf_acl': {'a-in': '10.100.1.2/30',  'a-out': '10.100.2.1/30', 'acl-mgmt': '192.168.99.3/24'},
    'vnf_qos': {'q-in': '10.100.2.2/30',  'q-out': '10.100.3.1/30', 'qos-mgmt': '192.168.99.4/24'},
    'r_isp':   {'isp-in': '10.100.3.2/30', 'isp-core': '10.200.0.1/30'},
    'r_core':  {'core-isp': '10.200.0.2/30', 'core-lan': '172.20.20.1/24'},
    'vnf_mon': {'mon-mgmt': '192.168.99.100/24'},
}

# Interfaces de dados (as que levam tráfego de utilizador)
DATA_INTFS = {
    'vnf_cls': ['c-in', 'c-out'],
    'vnf_acl': ['a-in', 'a-out'],
    'vnf_qos': ['q-in', 'q-out'],
    'r_isp':   ['isp-in', 'isp-core'],
    'r_core':  ['core-isp', 'core-lan'],
}


def prepare_host_kernel():
    """Garante que o Docker/WSL não bloqueia pacotes nas bridges do Open vSwitch."""
    subprocess.run('iptables -P FORWARD ACCEPT 2>/dev/null || true', shell=True)
    subprocess.run('sysctl -w net.bridge.bridge-nf-call-iptables=0 >/dev/null 2>&1 || true', shell=True)
    subprocess.run('sysctl -w net.bridge.bridge-nf-call-ip6tables=0 >/dev/null 2>&1 || true', shell=True)


def docker(net, name, forward=False):
    """Cria um nó Docker com NET_ADMIN (tc, nftables) e o repo montado em /workspace."""
    params = dict(
        dimage=IMG,
        volumes=[f'{REPO}:/workspace:rw'],
        cap_add=['NET_ADMIN', 'NET_RAW'],
        privileged=True,
    )
    if forward:
        params['sysctls'] = {
            'net.ipv4.ip_forward': 1,
            'net.ipv4.conf.all.rp_filter': 0,
            'net.ipv4.conf.default.rp_filter': 0,
        }
    return net.addDocker(name, **params)


def build(net):
    info('*** Comutadores OVS (standalone)\n')
    s1 = net.addSwitch('s1', cls=OVSSwitch, failMode='standalone')  # LAN clientes
    s2 = net.addSwitch('s2', cls=OVSSwitch, failMode='standalone')  # LAN servidores
    s3 = net.addSwitch('s3', cls=OVSSwitch, failMode='standalone')  # gestão

    info('*** Hosts (Clientes e Servidores)\n')
    nodes = {}
    for name in CLIENTES:
        nodes[name] = docker(net, name)
        net.addLink(nodes[name], s1, intfName1=f'{name}-eth0'[:15])
    for name in SERVIDORES:
        nodes[name] = docker(net, name)
        net.addLink(nodes[name], s2, intfName1=f'{name}-eth0'[:15])

    info('*** Cadeia de VNFs e Routers ISP\n')
    for name in ('vnf_cls', 'vnf_acl', 'vnf_qos', 'r_isp', 'r_core'):
        nodes[name] = docker(net, name, forward=True)
    nodes['vnf_mon'] = docker(net, 'vnf_mon')

    cls_n, acl_n, qos_n, isp_n, core_n = (
        nodes[n] for n in ('vnf_cls', 'vnf_acl', 'vnf_qos', 'r_isp', 'r_core')
    )

    info('*** Ligações do caminho de dados (SFC)\n')
    net.addLink(cls_n, s1, intfName1='c-in')
    net.addLink(cls_n, acl_n, intfName1='c-out', intfName2='a-in')
    net.addLink(acl_n, qos_n, intfName1='a-out', intfName2='q-in')
    net.addLink(qos_n, isp_n, intfName1='q-out', intfName2='isp-in')
    net.addLink(isp_n, core_n, intfName1='isp-core', intfName2='core-isp')
    net.addLink(core_n, s2, intfName1='core-lan')

    info('*** Rede de gestão Out-of-Band\n')
    for name in GESTAO:
        short = name.replace('vnf_', '')
        net.addLink(nodes[name], s3, intfName1=f'{short}-mgmt')
    return nodes


def sh(node, cmd):
    out = node.cmd(cmd).strip()
    if any(k in out for k in ('rror', 'RTNETLINK', 'denied', 'not found', 'No such', 'Cannot')):
        error(f'[{node.name}] {cmd}\n  -> {out}\n')
    return out


def set_ip(node, intf, cidr):
    """Remove qualquer IP existente (ex.: 10.0.0.x/8 do Mininet) e põe o correto."""
    sh(node, f'ip addr flush dev {intf}')
    sh(node, f'ip addr add {cidr} dev {intf}')
    sh(node, f'ip link set dev {intf} up')


def configure(nodes, access_bw, core_bw, core_delay):
    info('*** IPs explícitos (flush + add)\n')
    for name, ip in CLIENTES.items():
        set_ip(nodes[name], f'{name}-eth0'[:15], f'{ip}/24')
    for name, ip in SERVIDORES.items():
        set_ip(nodes[name], f'{name}-eth0'[:15], f'{ip}/24')
    for name, intfs in IPS.items():
        for intf, cidr in intfs.items():
            set_ip(nodes[name], intf, cidr)

    info('*** Sysctls (IP forwarding e rp_filter) nas VNFs e routers\n')
    for name, intfs in DATA_INTFS.items():
        sh(nodes[name], 'sysctl -w net.ipv4.ip_forward=1')
        sh(nodes[name], 'sysctl -w net.ipv4.conf.all.rp_filter=0')
        sh(nodes[name], 'sysctl -w net.ipv4.conf.default.rp_filter=0')
        for intf in intfs:
            sh(nodes[name], f'sysctl -w net.ipv4.conf.{intf}.rp_filter=0')

    info('*** Rotas estáticas\n')
    for name in CLIENTES:
        sh(nodes[name], 'ip route replace default via 172.20.10.1')
    for name in SERVIDORES:
        sh(nodes[name], 'ip route replace default via 172.20.20.1')

    sh(nodes['vnf_cls'], 'ip route replace default via 10.100.1.2')
    sh(nodes['vnf_acl'], 'ip route replace default via 10.100.2.2')
    sh(nodes['vnf_acl'], 'ip route replace 172.20.10.0/24 via 10.100.1.1')
    sh(nodes['vnf_qos'], 'ip route replace default via 10.100.3.2')
    sh(nodes['vnf_qos'], 'ip route replace 172.20.10.0/24 via 10.100.2.1')
    sh(nodes['r_isp'],   'ip route replace 172.20.10.0/24 via 10.100.3.1')
    sh(nodes['r_isp'],   'ip route replace default via 10.200.0.2')
    sh(nodes['r_core'],  'ip route replace default via 10.200.0.1')

    info('*** Offloads desligados (tc preciso em veth)\n')
    for name, intfs in DATA_INTFS.items():
        for intf in intfs:
            nodes[name].cmd(f'ethtool -K {intf} tso off gso off gro off 2>/dev/null')

    info(f'*** Ligação de acesso: {access_bw} Mbit/s (tbf, FIFO)\n')
    for node, intf in ((nodes['vnf_qos'], 'q-out'), (nodes['r_isp'], 'isp-in')):
        sh(node, f'tc qdisc replace dev {intf} root tbf rate {access_bw}mbit '
                 f'burst 32kbit latency 100ms')

    info(f'*** Núcleo: {core_bw} Mbit/s, {core_delay} por sentido (netem)\n')
    for node, intf in ((nodes['r_isp'], 'isp-core'), (nodes['r_core'], 'core-isp')):
        sh(node, f'tc qdisc replace dev {intf} root netem delay {core_delay} '
                 f'rate {core_bw}mbit limit 10000')


def check(nodes):
    info('*** Teste de conectividade (cliente -> servidor)\n')
    falhas = 0
    for c in CLIENTES:
        for s, ip in SERVIDORES.items():
            out = nodes[c].cmd(f'ping -c 2 -W 1 {ip}')
            ok = ' 0% packet loss' in out
            falhas += not ok
            info(f'  {c:10s} -> {s:10s} {"OK" if ok else "FALHOU"}\n')
    info('*** Teste da rede de gestão (vnf_mon -> VNFs)\n')
    for name, ip in GESTAO.items():
        if name == 'vnf_mon':
            continue
        ok = ' 0% packet loss' in nodes['vnf_mon'].cmd(f'ping -c 1 -W 1 {ip}')
        falhas += not ok
        info(f'  vnf_mon    -> {name:10s} {"OK" if ok else "FALHOU"}\n')
    info(f'*** {"Tudo OK!" if not falhas else f"{falhas} testes falharam"}\n')
    return falhas


def main():
    ap = argparse.ArgumentParser(description='Topologia TP3 QoSI (Containernet)')
    ap.add_argument('--access-bw', type=float, default=10, help='Mbit/s da ligação de acesso')
    ap.add_argument('--core-bw', type=float, default=100, help='Mbit/s do núcleo')
    ap.add_argument('--core-delay', default='10ms', help='atraso do núcleo por sentido')
    ap.add_argument('--test', action='store_true', help='testa conectividade e sai')
    args = ap.parse_args()

    setLogLevel('info')
    prepare_host_kernel()
    net = Containernet(controller=None)
    rc = 0
    try:
        nodes = build(net)
        net.start()
        configure(nodes, args.access_bw, args.core_bw, args.core_delay)
        if args.test:
            rc = 1 if check(nodes) else 0
        else:
            check(nodes)
            info('*** Topologia pronta. Noutro terminal: sudo ./trafego/gerar_cenarios.sh\n')
            CLI(net)
    finally:
        net.stop()
    sys.exit(rc)


if __name__ == '__main__':
    main()