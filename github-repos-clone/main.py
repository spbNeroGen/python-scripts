import requests
import subprocess
import os

def fetch_github_repositories(username: str, token: str, output_file: str) -> list:
    """
    Извлекаем список всех репозиториев и сохраняет их в файл.
    username: Имя пользователя GitHub
    token: Токен доступа GitHub - https://github.com/settings/tokens
    """
    url = f"https://api.github.com/user/repos"
    headers = {"Authorization": f"token {token}"}
    params = {"per_page": 10, "page": 1}  # Параметры для постраничного запроса
    
    repositories = []
    with open(output_file, "w") as file:
        while True:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                print(f"Ошибка: {response.status_code}, {response.text}")
                break
            
            repos = response.json()
            if not repos:
                break
            
            for repo in repos:
                repo_data = {
                    "name": repo["name"],
                    "url": repo["clone_url"]
                }
                repositories.append(repo_data)
                file.write(f"Имя: {repo['name']}\n")
                file.write(f"URL: {repo['clone_url']}\n")
                file.write(f"Приватный: {'Да' if repo['private'] else 'Нет'}\n")
                file.write("---\n")
            
            params["page"] += 1  # Переход к следующей странице

    print(f"Список репозиториев сохранен в файл '{output_file}'.")
    return repositories

def clone_repositories(repositories: list, output_dir: str) -> None:
    """
    Клонируем все репозитории в директорию.
    """
    os.makedirs(output_dir, exist_ok=True)
    os.chdir(output_dir)
    
    for repo in repositories:
        repo_name = repo["name"]
        repo_url = repo["url"]
        
        if os.path.exists(repo_name):
            print(f"Репозиторий {repo_name} уже существует. Пропускаем.")
            continue
        
        print(f"\nКлонируем {repo_name} из {repo_url}...")
        try:
            subprocess.run(["git", "clone", repo_url], check=True)
            print(f"Репозиторий {repo_name} успешно клонирован.\n")
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при клонировании {repo_name}: {e}")


# Настройки
github_username = "nickname_github"
github_token = "" # https://github.com/settings/tokens

output_file_path = "repositories.txt"  # Файл для сохранения списка репозиториев
output_directory = "github_repositories"  # Директория для клонирования репозиториев


# Извлечение и клонирование репозиториев
repos = fetch_github_repositories(github_username, github_token, output_file_path)
if repos:
    clone_repositories(repos, output_directory)
else:
    print("Не удалось получить список репозиториев.")
