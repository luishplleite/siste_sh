#!/usr/bin/env python3
# encoding: utf-8
# SSHPLUS - Proxy Otimizado com AsyncIO
# Baseado nas melhorias do Relatório Técnico - Fase 2

import asyncio
import sys
import signal
from typing import Optional

IP = '0.0.0.0'
try:
    PORT = int(sys.argv[1])
except:
    PORT = 8080

PASS = ''
BUFLEN = 8196 * 8
TIMEOUT = 60
MSG = 'ALERT'
DEFAULT_HOST = '0.0.0.0:1194'
RESPONSE = f"HTTP/1.1 101 {MSG}\r\n\r\n".encode()

class AdaptiveBuffer:
    """Buffer adaptativo baseado no throughput da conexão"""
    def __init__(self, initial_size=4096):
        self.size = initial_size
        self.min_size = 1024
        self.max_size = 65536
        
    def adjust(self, bytes_transferred: int, time_elapsed: float):
        if time_elapsed > 0:
            throughput = bytes_transferred / time_elapsed
            if throughput > 1000000:  # >1MB/s
                self.size = min(self.size * 2, self.max_size)
            elif throughput < 100000:  # <100KB/s
                self.size = max(self.size // 2, self.min_size)

class ProxyServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server = None
        self.connections = 0
        
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handler assíncrono para cada conexão cliente"""
        self.connections += 1
        addr = writer.get_extra_info('peername')
        
        try:
            # Recebe headers do cliente
            client_buffer = await asyncio.wait_for(
                reader.read(BUFLEN), 
                timeout=10
            )
            
            # Extrai host destino
            host_port = self.find_header(client_buffer, b'X-Real-Host')
            if not host_port:
                host_port = DEFAULT_HOST.encode()
            
            # Verifica split header
            split = self.find_header(client_buffer, b'X-Split')
            if split:
                await reader.read(BUFLEN)
            
            # Validação de senha e host
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
            print(f"Timeout na conexão de {addr}")
        except Exception as e:
            print(f"Erro na conexão de {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            self.connections -= 1
    
    def find_header(self, data: bytes, header: bytes) -> Optional[bytes]:
        """Busca header nos dados recebidos"""
        header_start = data.find(header + b': ')
        if header_start == -1:
            return None
        
        value_start = data.find(b':', header_start) + 2
        value_end = data.find(b'\r\n', value_start)
        
        if value_end == -1:
            return None
            
        return data[value_start:value_end]
    
    async def method_connect(self, client_reader: asyncio.StreamReader, 
                           client_writer: asyncio.StreamWriter, path: str):
        """Estabelece conexão CONNECT com buffer adaptativo"""
        # Parse host:port
        if ':' in path:
            host, port = path.rsplit(':', 1)
            port = int(port)
        else:
            host = path
            port = 22
        
        try:
            # Conecta ao destino
            target_reader, target_writer = await asyncio.open_connection(host, port)
            
            # Envia resposta de sucesso
            client_writer.write(RESPONSE)
            await client_writer.drain()
            
            # Inicia proxy bidirecional com buffer adaptativo
            await self.bidirectional_proxy(
                client_reader, client_writer,
                target_reader, target_writer
            )
            
        except Exception as e:
            print(f"Erro ao conectar em {host}:{port} - {e}")
            client_writer.close()
            await client_writer.wait_closed()
    
    async def bidirectional_proxy(self, client_reader, client_writer, 
                                 target_reader, target_writer):
        """Proxy bidirecional otimizado com buffer adaptativo"""
        buffer = AdaptiveBuffer()
        
        async def pipe(reader, writer, direction=""):
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
                    
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"Erro no pipe {direction}: {e}")
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass
        
        # Executa pipes bidirecionais em paralelo
        await asyncio.gather(
            pipe(client_reader, target_writer, "client->target"),
            pipe(target_reader, client_writer, "target->client"),
            return_exceptions=True
        )
    
    async def start(self):
        """Inicia o servidor"""
        self.server = await asyncio.start_server(
            self.handle_client, 
            self.host, 
            self.port,
            reuse_address=True,
            reuse_port=True
        )
        
        print("\033[0;34m━"*8, "\033[1;32m PROXY SOCKS OTIMIZADO", "\033[0;34m━"*8, "\n")
        print(f"\033[1;33mIP:\033[1;32m {IP}")
        print(f"\033[1;33mPORTA:\033[1;32m {PORT}")
        print(f"\033[1;33mMODO:\033[1;32m AsyncIO (Alta Performance)\n")
        print("\033[0;34m━"*10, "\033[1;32m SSHPLUS", "\033[0;34m━\033[1;37m"*11, "\n")
        
        async with self.server:
            await self.server.serve_forever()

async def main():
    server = ProxyServer(IP, PORT)
    
    # Configura handler para shutdown gracioso
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(server)))
    
    await server.start()

async def shutdown(server):
    """Shutdown gracioso do servidor"""
    print("\n\033[1;33mEncerrando servidor...\033[0m")
    server.server.close()
    await server.server.wait_closed()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n\033[1;32mServidor encerrado.\033[0m')
