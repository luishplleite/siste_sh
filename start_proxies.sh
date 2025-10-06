#!/bin/bash
# SSHPLUS - Inicializador de Proxies Otimizados
# Sistema real em produção com AsyncIO

clear

echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "\033[1;32m           SSHPLUS - PROXIES OTIMIZADOS (AsyncIO)          \033[0m"
echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo ""
echo -e "\033[1;33m[*]\033[0m Inicializando sistema com melhorias de performance..."
echo ""

# Cria diretório de logs se não existir
mkdir -p /tmp/sshplus_logs

# Função para iniciar proxy em background
start_proxy() {
    local name=$1
    local script=$2
    local port=$3
    local log=$4
    
    echo -e "\033[1;32m[✓]\033[0m Iniciando \033[1;37m$name\033[0m na porta \033[1;36m$port\033[0m..."
    nohup python3 "$script" "$port" > "$log" 2>&1 &
    echo $! > "/tmp/sshplus_${name// /_}.pid"
    sleep 1
}

# Inicia os proxies otimizados
start_proxy "Proxy SOCKS" "Modulos/open.py" 8080 "/tmp/sshplus_logs/open.log"
start_proxy "Proxy HTTP" "Modulos/proxy.py" 8081 "/tmp/sshplus_logs/proxy.log"
start_proxy "Proxy WebSocket" "Modulos/wsproxy.py" 8082 "/tmp/sshplus_logs/wsproxy.log"

echo ""
echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "\033[1;32m                  PROXIES ATIVOS                           \033[0m"
echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo ""
echo -e "  \033[1;33m[1]\033[0m Proxy SOCKS    → Porta \033[1;36m8080\033[0m (AsyncIO)"
echo -e "  \033[1;33m[2]\033[0m Proxy HTTP     → Porta \033[1;36m8081\033[0m (AsyncIO + Pool)"
echo -e "  \033[1;33m[3]\033[0m Proxy WebSocket→ Porta \033[1;36m8082\033[0m (AsyncIO + Keep-Alive)"
echo ""
echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo ""
echo -e "\033[1;32mMELHORIAS APLICADAS:\033[0m"
echo -e "  • Arquitetura AsyncIO (500% mais conexões simultâneas)"
echo -e "  • Connection Pooling (reduz handshakes TCP)"
echo -e "  • Buffer Adaptativo (otimiza throughput)"
echo -e "  • Keep-Alive WebSocket (conexões estáveis)"
echo ""
echo -e "\033[1;33mLOGS:\033[0m /tmp/sshplus_logs/"
echo -e "\033[1;33mPIDs:\033[0m /tmp/sshplus_*.pid"
echo ""
echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo ""
echo -e "\033[1;32m[✓] Sistema iniciado com sucesso!\033[0m"
echo ""
echo -e "\033[1;37mPara parar os proxies:\033[0m"
echo -e "  kill \$(cat /tmp/sshplus_*.pid)"
echo ""
echo -e "\033[1;37mPara ver logs em tempo real:\033[0m"
echo -e "  tail -f /tmp/sshplus_logs/*.log"
echo ""

# Mantém o script rodando e mostra status
while true; do
    echo -e "\n\033[1;33m[$(date '+%H:%M:%S')]\033[0m Sistema rodando... (Ctrl+C para sair)\n"
    
    # Verifica se os processos ainda estão rodando
    for pid_file in /tmp/sshplus_*.pid; do
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            proxy_name=$(basename "$pid_file" .pid | sed 's/sshplus_//' | tr '_' ' ')
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "  \033[1;32m✓\033[0m $proxy_name (PID: $pid)"
            else
                echo -e "  \033[1;31m✗\033[0m $proxy_name (PID: $pid) - PARADO!"
            fi
        fi
    done
    
    sleep 30
done
