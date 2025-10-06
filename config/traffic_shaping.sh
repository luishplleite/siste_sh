#!/bin/bash
# SSHPLUS - Traffic Shaping (QoS) Script
# Baseado no Relatório Técnico de Melhorias - Fase 2
#
# Este script implementa QoS usando tc (Traffic Control) com HTB + fq_codel
# para priorizar tráfego de VPN/SSH e reduzir bufferbloat

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Interface de rede (ajuste conforme necessário)
INTERFACE="eth0"

# Velocidade do link (ajuste conforme sua conexão)
# Valores em mbit (megabits)
DOWNLINK=100
UPLINK=100

echo -e "${YELLOW}========================================${NC}"
echo -e "${GREEN}  SSHPLUS - Traffic Shaping Setup${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Verifica se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Este script precisa ser executado como root${NC}"
    exit 1
fi

# Verifica se tc está instalado
if ! command -v tc &> /dev/null; then
    echo -e "${RED}tc (Traffic Control) não encontrado!${NC}"
    echo -e "${YELLOW}Instale com: apt-get install iproute2${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/5]${NC} Limpando regras existentes..."
# Limpa regras existentes
tc qdisc del dev $INTERFACE root 2>/dev/null || true
tc qdisc del dev $INTERFACE ingress 2>/dev/null || true

echo -e "${YELLOW}[2/5]${NC} Criando qdisc raiz HTB..."
# Cria qdisc raiz do tipo HTB (Hierarchical Token Bucket)
tc qdisc add dev $INTERFACE root handle 1: htb default 30

# Cria classe raiz
tc class add dev $INTERFACE parent 1: classid 1:1 htb rate ${UPLINK}mbit

echo -e "${YELLOW}[3/5]${NC} Configurando classes de prioridade..."

# ========================================
# CLASSE 1:10 - PRIORIDADE ALTA (VPN/SSH)
# ========================================
# 40% da banda garantida, pode usar até 80% se disponível
tc class add dev $INTERFACE parent 1:1 classid 1:10 htb \
    rate $((UPLINK*40/100))mbit \
    ceil $((UPLINK*80/100))mbit \
    prio 0

# Anexa fq_codel para combater bufferbloat
tc qdisc add dev $INTERFACE parent 1:10 handle 10: fq_codel \
    quantum 300 \
    limit 10240 \
    flows 1024 \
    target 5ms \
    interval 100ms

# ========================================
# CLASSE 1:20 - PRIORIDADE MÉDIA (Web/HTTPS)
# ========================================
# 30% da banda garantida, pode usar até 60% se disponível
tc class add dev $INTERFACE parent 1:1 classid 1:20 htb \
    rate $((UPLINK*30/100))mbit \
    ceil $((UPLINK*60/100))mbit \
    prio 1

tc qdisc add dev $INTERFACE parent 1:20 handle 20: fq_codel

# ========================================
# CLASSE 1:30 - PRIORIDADE BAIXA (Bulk/Outros)
# ========================================
# 30% da banda garantida, pode usar até 100% se disponível
tc class add dev $INTERFACE parent 1:1 classid 1:30 htb \
    rate $((UPLINK*30/100))mbit \
    ceil ${UPLINK}mbit \
    prio 2

tc qdisc add dev $INTERFACE parent 1:30 handle 30: fq_codel

echo -e "${YELLOW}[4/5]${NC} Criando filtros de tráfego..."

# ========================================
# FILTROS - Direciona tráfego para classes
# ========================================

# Prioridade 0 (Alta): SSH (porta 22)
tc filter add dev $INTERFACE parent 1:0 protocol ip prio 1 u32 \
    match ip dport 22 0xffff \
    flowid 1:10

tc filter add dev $INTERFACE parent 1:0 protocol ip prio 1 u32 \
    match ip sport 22 0xffff \
    flowid 1:10

# Prioridade 0 (Alta): OpenVPN (porta 1194)
tc filter add dev $INTERFACE parent 1:0 protocol ip prio 1 u32 \
    match ip dport 1194 0xffff \
    flowid 1:10

tc filter add dev $INTERFACE parent 1:0 protocol ip prio 1 u32 \
    match ip sport 1194 0xffff \
    flowid 1:10

# Prioridade 0 (Alta): DNS (porta 53)
tc filter add dev $INTERFACE parent 1:0 protocol ip prio 1 u32 \
    match ip dport 53 0xffff \
    flowid 1:10

tc filter add dev $INTERFACE parent 1:0 protocol ip prio 1 u32 \
    match ip sport 53 0xffff \
    flowid 1:10

# Prioridade 1 (Média): HTTP (porta 80)
tc filter add dev $INTERFACE parent 1:0 protocol ip prio 2 u32 \
    match ip dport 80 0xffff \
    flowid 1:20

# Prioridade 1 (Média): HTTPS (porta 443)
tc filter add dev $INTERFACE parent 1:0 protocol ip prio 2 u32 \
    match ip dport 443 0xffff \
    flowid 1:20

# WireGuard (porta 51820) - Alta prioridade
tc filter add dev $INTERFACE parent 1:0 protocol ip prio 1 u32 \
    match ip dport 51820 0xffff \
    flowid 1:10

echo -e "${YELLOW}[5/5]${NC} Verificando configuração..."
echo ""

# Mostra configuração
echo -e "${GREEN}=== Qdiscs ===${NC}"
tc qdisc show dev $INTERFACE

echo ""
echo -e "${GREEN}=== Classes ===${NC}"
tc class show dev $INTERFACE

echo ""
echo -e "${GREEN}=== Filtros ===${NC}"
tc filter show dev $INTERFACE

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Traffic Shaping aplicado com sucesso!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Para remover:${NC} tc qdisc del dev $INTERFACE root"
echo -e "${YELLOW}Para monitorar:${NC} watch -n1 tc -s class show dev $INTERFACE"
echo ""
echo -e "${YELLOW}NOTA:${NC} Este script não funciona no Replit devido a"
echo -e "      restrições de segurança. Use em VPS/servidor dedicado."
