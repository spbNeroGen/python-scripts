import paramiko  # type: ignore
from typing import List, Dict

def get_ssh_client(host: str, username: str, key_path: str, timeout: int = 10) -> paramiko.SSHClient:
    """Устанавливает SSH-соединение с указанным сервером"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, username=username, key_filename=key_path, timeout=timeout)
        print(f"Подключение к {host} установлено.")
    except Exception as e:
        print(f"Не удалось подключиться к {host}: {e}")
        return None
    return client

def execute_command(client: paramiko.SSHClient, command: str) -> str:
    """Выполняет команду на удаленном сервере и возвращает результат"""
    stdin, stdout, stderr = client.exec_command(command)
    return stdout.read().decode()

def analyze_disk_usage(client: paramiko.SSHClient) -> str:
    """Анализ дискового пространства"""
    command = "df -h"
    return execute_command(client, command)

def analyze_docker_images(client: paramiko.SSHClient) -> str:
    """Анализ Docker образов"""
    command = "docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'"
    return execute_command(client, command)

def analyze_docker_containers(client: paramiko.SSHClient) -> str:
    """Анализ Docker контейнеров"""
    command = "docker ps --format 'table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}'"
    return execute_command(client, command)

def load_server_list(file_path: str) -> List[Dict[str, str]]:
    """Загружает список серверов из файла и возвращает его в виде списка словарей."""
    servers = []
    with open(file_path, 'r') as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) >= 3:
                server = {
                    "host": parts[0],
                    "name": parts[1],
                    "type": parts[2]
                }
                servers.append(server)
    return servers

def inventory_agents(server_file: str, output_file: str, username: str, key_path: str) -> None:
    """Собирает информацию о каждом агенте и сохраняет её в файл."""
    servers = load_server_list(server_file)
    with open(output_file, 'w') as output:
        for server in servers:
            host = server["host"]
            name = server["name"]
            server_type = server["type"]
            
            output.write(f"\n### Инвентаризация агента - *{name}* ({host}, тип: {server_type})\n")
            print(f"\n=== Инвентаризация агента - {name} ({host}, тип: {server_type}) ===")

            client = get_ssh_client(host, username, key_path)
            if not client:
                output.write(f">Не удалось подключиться к {host}\n")
                continue

            # Анализ дискового пространства
            output.write("\n#### Дисковое пространство\n\n```bash\n")
            output.write(analyze_disk_usage(client) + "```\n")

            # Анализ Docker образов
            output.write("\n#### Docker образы:\n\n```bash\n")
            output.write(analyze_docker_images(client) + "```\n")

            # Анализ Docker контейнеров
            output.write("\n#### Docker запущенные контейнеры\n\n```bash\n")
            output.write(analyze_docker_containers(client) + "```\n")

            output.write("\n---\n")
            client.close()
            print(f"Отключение от {host} завершено.")

# Основные настройки
server_file_path = "server.txt"   # файл со списком серверов
output_file_path = "output.md"   # файл для вывода
ssh_username = "ubuntu"           # имя пользователя для подключения
ssh_key_path = "~/.ssh/id_ed25519"  # путь к SSH-ключу

# Запуск инвентаризации
inventory_agents(server_file_path, output_file_path, ssh_username, ssh_key_path)
