#!/usr/bin/env python3
# encoding: utf-8
# SSHPLUS - Proxy WebSocket Otimizado com AsyncIO
# Baseado nas melhorias do Relatório Técnico - Fase 2

import asyncio
import sys
import signal
import getopt
from typing import Optional

PASS = ''
LISTENING_ADDR = '0.0.0.0'
try:
    LISTENING_PORT = int(sys.argv[1])
except:
    LISTENING_PORT = 80

BUFLEN = 4096 * 4
TIMEOUT = 60
MSG = ''
COR = '<font color="null">'
FTAG = '</font>'
DEFAULT_HOST = "127.0.0.1:22"
RESPONSE = f"HTTP/1.1 101 {COR}{MSG}{FTAG}\r\n\r\n".encode()

class WSMetrics:
    """Métricas para monitoramento Prometheus"""
    def __init__(self):
        self.total_connections = 0
        self.active_connections = 0
        self.total_bytes_sent = 0
        self.total_bytes_received = 0
        
    def log_metrics(self):
        """Log estruturado de métricas"""
        return {
            'total_connections': self.total_connections,
            'active_connections': self.active_connections,
            'total_bytes_sent': self.total_bytes_sent,
            'total_bytes_received': self.total_bytes_received
        }

class AdaptiveBuffer:
    """Buffer adaptativo para otimizar throughput"""
    def __init__(self, initial_size=4096):
        self.size = initial_size
        self.min_size = 1024
        self.max_size = 65536
        
    def adjust(self, bytes_transferred: int, time_elapsed: float):
        if time_elapsed > 0:
            throughput = bytes_transferred / time_elapsed
            if throughput > 1000000:
                self.size = min(self.size * 2, self.max_size)
            elif throughput < 100000:
                self.size = max(self.size // 2, self.min_size)

class WebSocketProxyServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server = None
        self.metrics = WSMetrics()
        
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handler otimizado para WebSocket"""
        self.metrics.total_connections += 1
        self.metrics.active_connections += 1
        addr = writer.get_extra_info('peername')
        
        try:
            client_buffer = await asyncio.wait_for(reader.read(BUFLEN), timeout=10)
            
            host_port = self.find_header(client_buffer, b'X-Real-Host')
            if not host_port:
                host_port = DEFAULT_HOST.encode()
            
            split = self.find_header(client_buffer, b'X-Split')
            if split:
                await reader.read(BUFLEN)
            
            if host_port:
                passwd = self.find_header(client_buffer, b'X-Pass')
                host_str = host_port.decode()
                
                if len(PASS) != 0 and passwd and passwd.decode() == PASS:
                    await self.method_connect(reader, writer, host_str, addr)
                elif len(PASS) != 0 and (not passwd or passwd.decode() != PASS):
                    writer.write(b'HTTP/1.1 400 WrongPass!\r\n\r\n')
                    await writer.drain()
                elif len(PASS) == 0:
                    await self.method_connect(reader, writer, host_str, addr)
                elif host_str.startswith('127.0.0.1') or host_str.startswith('localhost'):
                    await self.method_connect(reader, writer, host_str, addr)
                else:
                    writer.write(b'HTTP/1.1 403 Forbidden!\r\n\r\n')
                    await writer.drain()
            else:
                writer.write(b'HTTP/1.1 400 NoXRealHost!\r\n\r\n')
                await writer.drain()
                
        except asyncio.TimeoutError:
            print(f"Timeout: {addr}")
        except Exception as e:
            print(f"Erro {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            self.metrics.active_connections -= 1
    
    def find_header(self, data: bytes, header: bytes) -> Optional[bytes]:
        """Busca header nos dados"""
        header_start = data.find(header + b': ')
        if header_start == -1:
            return None
        
        value_start = data.find(b':', header_start) + 2
        value_end = data.find(b'\r\n', value_start)
        
        if value_end == -1:
            return None
            
        return data[value_start:value_end]
    
    async def method_connect(self, client_reader, client_writer, path: str, addr):
        """WebSocket CONNECT com keep-alive"""
        if ':' in path:
            host, port = path.rsplit(':', 1)
            port = int(port)
        else:
            host = path
            port = 80
        
        try:
            target_reader, target_writer = await asyncio.open_connection(host, port)
            
            print(f"Conectado: {addr} -> {host}:{port}")
            
            client_writer.write(RESPONSE)
            await client_writer.drain()
            
            await self.bidirectional_proxy_with_keepalive(
                client_reader, client_writer,
                target_reader, target_writer
            )
            
        except Exception as e:
            print(f"Erro conectando {host}:{port} - {e}")
            client_writer.close()
            await client_writer.wait_closed()
    
    async def bidirectional_proxy_with_keepalive(self, client_reader, client_writer, 
                                                target_reader, target_writer):
        """Proxy com auto-ping para keep-alive WebSocket"""
        buffer = AdaptiveBuffer()
        keepalive_interval = 30  # ping a cada 30s
        
        async def pipe(reader, writer, direction=""):
            bytes_transferred = 0
            try:
                while True:
                    data = await asyncio.wait_for(
                        reader.read(buffer.size), 
                        timeout=TIMEOUT
                    )
                    if not data:
                        break
                    
                    writer.write(data)
                    await writer.drain()
                    bytes_transferred += len(data)
                    
                    if direction == "server->client":
                        self.metrics.total_bytes_sent += len(data)
                    else:
                        self.metrics.total_bytes_received += len(data)
                        
            except (asyncio.TimeoutError, Exception) as e:
                pass
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass
        
        async def keepalive_ping(writer):
            """Envia ping periódico para manter conexão"""
            try:
                while not writer.is_closing():
                    await asyncio.sleep(keepalive_interval)
                    # WebSocket ping frame (0x89)
                    writer.write(b'\x89\x00')
                    await writer.drain()
            except:
                pass
        
        await asyncio.gather(
            pipe(client_reader, target_writer, "client->server"),
            pipe(target_reader, client_writer, "server->client"),
            keepalive_ping(client_writer),
            return_exceptions=True
        )
    
    async def start(self):
        """Inicia servidor WebSocket"""
        self.server = await asyncio.start_server(
            self.handle_client, 
            self.host, 
            self.port,
            reuse_address=True,
            reuse_port=True
        )
        
        print("\033[0;34m━"*8, "\033[1;32m PROXY WEBSOCKET OTIMIZADO", "\033[0;34m━"*8, "\n")
        print(f"\033[1;33mIP:\033[1;32m {LISTENING_ADDR}")
        print(f"\033[1;33mPORTA:\033[1;32m {LISTENING_PORT}")
        print(f"\033[1;33mMODO:\033[1;32m AsyncIO + Keep-Alive\n")
        print("\033[0;34m━"*10, "\033[1;32m VPSMANAGER", "\033[0;34m━\033[1;37m"*11, "\n")
        
        async with self.server:
            await self.server.serve_forever()

def print_usage():
    print('Use: wsproxy_async.py -p <port>')
    print('     wsproxy_async.py -b <ip> -p <porta>')
    print('     wsproxy_async.py -b 0.0.0.0 -p 80')

def parse_args(argv):
    global LISTENING_ADDR, LISTENING_PORT
    
    try:
        opts, args = getopt.getopt(argv, "hb:p:", ["bind=", "port="])
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == '-h':
            print_usage()
            sys.exit()
        elif opt in ("-b", "--bind"):
            LISTENING_ADDR = arg
        elif opt in ("-p", "--port"):
            LISTENING_PORT = int(arg)

async def main():
    server = WebSocketProxyServer(LISTENING_ADDR, LISTENING_PORT)
    
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(server)))
    
    await server.start()

async def shutdown(server):
    print("\n\033[1;33mEncerrando servidor...\033[0m")
    print(f"\033[1;36mMétricas finais: {server.metrics.log_metrics()}\033[0m")
    server.server.close()
    await server.server.wait_closed()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        parse_args(sys.argv[1:])
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n\033[1;32mServidor encerrado.\033[0m')
