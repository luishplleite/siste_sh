#!/usr/bin/env python3
# encoding: utf-8
# SSHPLUS - Proxy HTTP Otimizado com AsyncIO
# Baseado nas melhorias do Relatório Técnico - Fase 2

import asyncio
import sys
import signal
from typing import Optional

IP = '0.0.0.0'
try:
    PORT = int(sys.argv[1])
except:
    PORT = 80

PASS = ''
BUFLEN = 8196 * 8
TIMEOUT = 60
MSG = ''
COR = '<font color="null">'
FTAG = '</font>'
DEFAULT_HOST = '0.0.0.0:22'
RESPONSE = f"HTTP/1.1 200 {COR}{MSG}{FTAG}\r\n\r\n".encode()

class ConnectionPool:
    """Pool de conexões para reutilização - reduz overhead de handshakes TCP"""
    def __init__(self, max_size=100):
        self.pool = {}
        self.max_size = max_size
        self.lock = asyncio.Lock()
    
    async def get_connection(self, host: str, port: int):
        """Obtém conexão do pool ou cria nova"""
        key = f"{host}:{port}"
        
        async with self.lock:
            if key in self.pool and self.pool[key]:
                reader, writer = self.pool[key].pop()
                if not writer.is_closing():
                    return reader, writer
        
        # Cria nova conexão
        return await asyncio.open_connection(host, port)
    
    async def return_connection(self, host: str, port: int, reader, writer):
        """Retorna conexão ao pool"""
        key = f"{host}:{port}"
        
        async with self.lock:
            if key not in self.pool:
                self.pool[key] = []
            
            if len(self.pool[key]) < self.max_size and not writer.is_closing():
                self.pool[key].append((reader, writer))
            else:
                writer.close()
                await writer.wait_closed()

class AdaptiveBuffer:
    """Buffer adaptativo baseado no throughput"""
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

class ProxyServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server = None
        self.connections = 0
        self.pool = ConnectionPool()
        
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handler assíncrono para cada conexão cliente"""
        self.connections += 1
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
                
                if len(PASS) == 0:
                    await self.method_connect(reader, writer, host_port.decode())
                elif passwd and passwd.decode() == PASS:
                    await self.method_connect(reader, writer, host_port.decode())
                elif not passwd or passwd.decode() != PASS:
                    writer.write(b'HTTP/1.1 400 WrongPass!\r\n\r\n')
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
            self.connections -= 1
    
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
    
    async def method_connect(self, client_reader, client_writer, path: str):
        """Estabelece conexão CONNECT com pool de conexões"""
        if ':' in path:
            host, port = path.rsplit(':', 1)
            port = int(port)
        else:
            host = path
            port = 22
        
        try:
            target_reader, target_writer = await self.pool.get_connection(host, port)
            
            client_writer.write(RESPONSE)
            await client_writer.drain()
            
            await self.bidirectional_proxy(
                client_reader, client_writer,
                target_reader, target_writer
            )
            
        except Exception as e:
            print(f"Erro conectando {host}:{port} - {e}")
            client_writer.close()
            await client_writer.wait_closed()
    
    async def bidirectional_proxy(self, client_reader, client_writer, 
                                 target_reader, target_writer):
        """Proxy bidirecional com buffer adaptativo"""
        buffer = AdaptiveBuffer()
        
        async def pipe(reader, writer):
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
            except (asyncio.TimeoutError, Exception):
                pass
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass
        
        await asyncio.gather(
            pipe(client_reader, target_writer),
            pipe(target_reader, client_writer),
            return_exceptions=True
        )
    
    async def start(self):
        """Inicia servidor"""
        self.server = await asyncio.start_server(
            self.handle_client, 
            self.host, 
            self.port,
            reuse_address=True,
            reuse_port=True
        )
        
        print("\033[0;34m━"*8, "\033[1;32m PROXY HTTP OTIMIZADO", "\033[0;34m━"*8, "\n")
        print(f"\033[1;33mIP:\033[1;32m {IP}")
        print(f"\033[1;33mPORTA:\033[1;32m {PORT}")
        print(f"\033[1;33mMODO:\033[1;32m AsyncIO + Connection Pool\n")
        print("\033[0;34m━"*10, "\033[1;32m SSHPLUS", "\033[0;34m━\033[1;37m"*11, "\n")
        
        async with self.server:
            await self.server.serve_forever()

async def main():
    server = ProxyServer(IP, PORT)
    
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(server)))
    
    await server.start()

async def shutdown(server):
    print("\n\033[1;33mEncerrando servidor...\033[0m")
    server.server.close()
    await server.server.wait_closed()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n\033[1;32mServidor encerrado.\033[0m')
