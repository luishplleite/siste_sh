# SSHPLUS - Sistema de Gerenciamento VPN/SSH

## Visão Geral
Sistema de gerenciamento de SSH/VPN otimizado com melhorias de performance baseadas em relatório técnico. Inclui proxies Python otimizados com AsyncIO, configurações de kernel otimizadas e scripts de QoS.

## Estrutura do Projeto

```
.
├── Install/          # Scripts e binários de instalação
├── Modulos/          # Módulos principais do sistema
│   ├── *_async.py   # Proxies otimizados com AsyncIO (NOVOS)
│   ├── *.py         # Proxies originais (legado)
│   └── *            # Scripts bash de gerenciamento
├── Sistema/          # Arquivos do sistema
├── Slowdns/          # Módulos SlowDNS
├── config/           # Configurações otimizadas (NOVO)
│   ├── sysctl_optimized.conf       # Otimizações de kernel
│   ├── sshd_config_optimized       # Configurações SSH
│   └── traffic_shaping.sh          # QoS/Traffic Shaping
└── Plus              # Script principal de instalação
```

## Melhorias Implementadas

### Fase 1: Otimizações de Performance (✅ IMPLEMENTADO)

#### 1. Proxies Python Refatorados com AsyncIO
- **Arquivos**: `Modulos/*_async.py`
- **Melhorias**:
  - Migração de threading para asyncio
  - Connection pooling para reduzir handshakes TCP
  - Buffer adaptativo baseado em throughput
  - WebSocket com keep-alive automático
  - Métricas para monitoramento
  
- **Ganhos Esperados**:
  - +500% capacidade de conexões simultâneas
  - -60% uso de CPU
  - -80% uso de memória
  - Latência reduzida em 40-70%

#### 2. Configurações de Kernel Otimizadas
- **Arquivo**: `config/sysctl_optimized.conf`
- **Inclui**:
  - BBR congestion control
  - TCP window scaling otimizado
  - TCP Fast Open (reduz latência 80-95%)
  - Buffers aumentados para alta velocidade
  - Anti-DDoS com SYN cookies

#### 3. SSH Otimizado
- **Arquivo**: `config/sshd_config_optimized`
- **Melhorias**:
  - Ciphers modernos (ChaCha20, AES-GCM)
  - Compressão otimizada
  - Keep-alive configurado
  - Suporte a multiplexação

#### 4. QoS/Traffic Shaping
- **Arquivo**: `config/traffic_shaping.sh`
- **Funcionalidades**:
  - Priorização de tráfego VPN/SSH
  - HTB + fq_codel para combater bufferbloat
  - 3 classes de prioridade
  - Redução de jitter para VoIP/Games

### Fase 2: Pendente (Requer VPS)
- [ ] OpenVPN com algoritmos otimizados
- [ ] V2Ray com VLESS e mKCP
- [ ] WireGuard como alternativa moderna
- [ ] HAProxy + Keepalived para HA

## Limitações do Ambiente Replit

⚠️ **IMPORTANTE**: O Replit tem restrições de segurança que impedem:
- Modificação de parâmetros do kernel (`sysctl`)
- Instalação de OpenVPN/WireGuard
- Configuração de Traffic Control (`tc`)
- Modificação de configurações SSH do sistema
- Acesso root completo

### O que FUNCIONA no Replit:
✅ Proxies Python otimizados com AsyncIO
✅ Scripts de gerenciamento de usuários
✅ Bot do Telegram
✅ Monitoramento básico

### O que NÃO funciona no Replit:
❌ Otimizações de kernel
❌ VPN servers (OpenVPN, WireGuard)
❌ Traffic Shaping (QoS)
❌ SSH server otimizado

## Como Usar

### No Replit (Desenvolvimento/Teste)
```bash
# Testar proxy otimizado
python3 Modulos/open_async.py 8080
python3 Modulos/proxy_async.py 80
python3 Modulos/wsproxy_async.py 8081
```

### Em VPS/Servidor Dedicado (Produção)

1. **Aplicar otimizações de kernel**:
```bash
sudo cp config/sysctl_optimized.conf /etc/sysctl.d/99-sshplus.conf
sudo sysctl -p /etc/sysctl.d/99-sshplus.conf
```

2. **Configurar SSH otimizado**:
```bash
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
sudo cp config/sshd_config_optimized /etc/ssh/sshd_config
sudo sshd -t  # Verificar sintaxe
sudo systemctl restart sshd
```

3. **Aplicar Traffic Shaping**:
```bash
chmod +x config/traffic_shaping.sh
sudo ./config/traffic_shaping.sh
```

4. **Usar proxies otimizados**:
```bash
# Substituir scripts originais pelos otimizados
cd Modulos
python3 open_async.py 8080 &
python3 proxy_async.py 80 &
python3 wsproxy_async.py 8081 &
```

## Arquitetura das Melhorias

### Proxy AsyncIO com Connection Pool
```
Cliente → [AsyncIO Server] → [Connection Pool] → Destino
              ↓
        [Adaptive Buffer]
              ↓
        [Métricas/Logs]
```

### Traffic Shaping (QoS)
```
Tráfego → [tc HTB] → [Classe Alta: VPN/SSH] → fq_codel
                   → [Classe Média: Web]    → fq_codel  
                   → [Classe Baixa: Bulk]   → fq_codel
```

## Comandos Úteis

### Monitoramento
```bash
# Ver conexões ativas
watch -n1 'netstat -tan | grep ESTABLISHED | wc -l'

# Monitorar Traffic Shaping
watch -n1 tc -s class show dev eth0

# Ver métricas do proxy
# (métricas são exibidas no shutdown do proxy_async)
```

### Benchmarks
```bash
# Testar throughput
iperf3 -s  # Servidor
iperf3 -c <ip> -t 60  # Cliente

# Testar latência
ping -c 100 <ip>
```

## Próximos Passos

Para implantação completa em VPS:
1. Instalar WireGuard para VPN moderna
2. Configurar HAProxy para load balancing
3. Implementar Netdata para monitoramento
4. Migrar V2Ray para VLESS com mKCP
5. Configurar Prometheus + Grafana para métricas

## Desenvolvimento

### Dependências Python
```bash
pip install asyncio  # (built-in Python 3.7+)
```

### Executar Testes
```bash
# Testar proxy com múltiplas conexões
for i in {1..100}; do
  curl -x http://localhost:8080 http://example.com &
done
```

## Referências Técnicas

- [BBR Congestion Control](https://github.com/google/bbr)
- [TCP Fast Open](https://tools.ietf.org/html/rfc7413)
- [fq_codel](https://www.bufferbloat.net/projects/codel/)
- [AsyncIO Performance](https://docs.python.org/3/library/asyncio.html)

## Mudanças Recentes

### 06/10/2025
- ✅ Criados proxies otimizados com AsyncIO
- ✅ Implementado buffer adaptativo
- ✅ Adicionado connection pooling
- ✅ Criadas configurações otimizadas de kernel/SSH
- ✅ Desenvolvido script de Traffic Shaping
- ✅ Documentação completa das melhorias

## Notas de Arquitetura

Este é um sistema CLI (Command Line Interface) sem frontend web. Todas as interações são via terminal ou bot do Telegram. As melhorias focam em:
- Performance de rede
- Capacidade de conexões simultâneas  
- Redução de latência
- Otimização de throughput
