import os
import requests, urllib3
import subprocess, sys

from color import Color
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning

urllib3.disable_warnings(InsecureRequestWarning)

# Папка для скачанных артефактов RAW, самостоятельно создавать не обязательно
DOWNLOAD_DIR = "nexus_artifacts"

# Источник:
SOURCE_NEXUS_URL = "https://domain.example.com" 

# Пример SOURCE_NEXUS_URL = "https://domain.example.com" Важно! Без "/" на конце
SOURCE_SHORT_URL = urlparse(SOURCE_NEXUS_URL).hostname
SOURCE_REPOSITORY_NAME = "repo" 
SOURCE_USERNAME = "username" 
SOURCE_PASSWORD = "password"


# Куда загружаем:
TARGET_NEXUS_URL = "https://new.domain.example.com"
TARGET_SHORT_URL = urlparse(TARGET_NEXUS_URL).hostname
TARGET_REPOSITORY_NAME = "repo"  
TARGET_USERNAME = "username" 
TARGET_PASSWORD = "password"

def get_artifacts_from_nexus():
   '''Получаем json со списком артефактов'''
   url = f"{SOURCE_NEXUS_URL}/service/rest/v1/components?repository={SOURCE_REPOSITORY_NAME}"
   artifacts = []
   while url:
       response = requests.get(url, auth=HTTPBasicAuth(SOURCE_USERNAME, SOURCE_PASSWORD), verify=False)
       response.raise_for_status()
       data = response.json()
       artifacts.extend(data['items'])
       url = data.get('continuationToken')
       if url:
           url = f"{SOURCE_NEXUS_URL}/service/rest/v1/components?repository={SOURCE_REPOSITORY_NAME}&continuationToken={url}"
   return artifacts

def download_artifact(artifact):
   '''Скачиваем артефакт из Nexus, сохраняя структуру директорий'''
   for asset in artifact.get('assets', []):
       download_url = asset['downloadUrl']
       # Получаем  путь артефакта
       relative_path = asset['path']
       relative_path = relative_path.lstrip('/') # Убираем вначале лишний / если он есть
      
       # Полный путь для сохранения файла
       file_path = os.path.join(DOWNLOAD_DIR, relative_path)
       directory_path = os.path.dirname(file_path)
      
       # print(f"\nrelative_path {relative_path}") 
       # print(f"\nfile_path {file_path}")       
      
       # Проверяем и создаем папки для пути
       if os.path.exists(directory_path) and not os.path.isdir(directory_path):
           os.remove(directory_path)  # Удаляем файл, если он мешает создать папку
       os.makedirs(directory_path, exist_ok=True)
      
       # file_name = os.path.join(DOWNLOAD_DIR, asset['path'].replace('/', '_'))
       with requests.get(download_url, auth=HTTPBasicAuth(SOURCE_USERNAME, SOURCE_PASSWORD), stream=True, verify=False) as r:
           r.raise_for_status()
           with open(file_path, 'wb') as f:
               for chunk in r.iter_content(chunk_size=8192):
                   f.write(chunk)
       print(Color.GREEN + f"\nDownloaded {file_path}" + Color.END)
      
       # Загружаем файл в целевой репозиторий
       upload_to_target_nexus(file_path, relative_path)
      
def upload_to_target_nexus(file_path, relative_path):
   '''Загружаем файл в целевой Nexus репозиторий, сохраняя структуру директорий'''
   target_url = f"{TARGET_NEXUS_URL}/repository/{TARGET_REPOSITORY_NAME}/{relative_path}"
   with open(file_path, 'rb') as f:
       file_data = f.read()
       response = requests.put(target_url, auth=HTTPBasicAuth(TARGET_USERNAME, TARGET_PASSWORD), data=file_data, verify=False)
       response.raise_for_status()
       print(Color.YELLOW + f"Uploaded {file_path} to {target_url}" + Color.END)

def get_docker_images_from_nexus():
   '''Получаем список images из Nexus'''
   url = f"{SOURCE_NEXUS_URL}/service/rest/v1/components?repository={SOURCE_REPOSITORY_NAME}"
   docker_images = {}
   while url:
       response = requests.get(url, auth=HTTPBasicAuth(SOURCE_USERNAME, SOURCE_PASSWORD), verify=False)
       response.raise_for_status()
       data = response.json()
       for item in data['items']:
           image_name = item['name']
           tag = item['version']
           if image_name not in docker_images:
               docker_images[image_name] = []
           docker_images[image_name].append(tag)
       url = data.get('continuationToken')
       if url:
           url = f"{SOURCE_NEXUS_URL}/service/rest/v1/components?repository={SOURCE_REPOSITORY_NAME}&continuationToken={url}"
   return docker_images

def docker_login(repo_url, username, password):
   '''Для выполнения docker login в репозиторий.'''
   try:
       print(f"Logging in {repo_url}...")
       login_command = ["docker", "login", repo_url, "-u", username, "-p", password]
       result = subprocess.run(login_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
       print(Color.GREEN + f"Logged in {repo_url} successfully." + Color.END)
       return result
   except subprocess.CalledProcessError as e:
       print(Color.RED + f"Error while logging in to {repo_url}." + Color.END)
       print(Color.RED + f"Error: {e.stderr.decode()}" + Color.END)
       sys.exit(1)  # Завершаем выполнение при неудачной аутентификации
  
def migrate_docker_images(images):
   '''Для выполнения docker миграции'''
   docker_login(SOURCE_SHORT_URL, SOURCE_USERNAME, SOURCE_PASSWORD)    # Авторизация
   docker_login(TARGET_SHORT_URL, TARGET_USERNAME, TARGET_PASSWORD)
  
   for image, tags in images.items():
       for tag in tags:
           source_image = f'{SOURCE_SHORT_URL}/{image}:{tag}'
           image_name_cleaned = image[len(SOURCE_REPOSITORY_NAME)+1:]
           target_image = f'{TARGET_SHORT_URL}/{TARGET_REPOSITORY_NAME}/{image_name_cleaned}:{tag}'
           # Скачиваем образ
           print(Color.YELLOW + f"\nNow Pull image {source_image}" + Color.END)
           subprocess.run(['docker', 'pull', source_image], check=True)
           # Перетегирование
           print(Color.GREEN + f"\nNow Tag {source_image} as {target_image}" + Color.END)
           subprocess.run(["docker", "tag", source_image, target_image], check=True)
          
           # Пушим
           print(Color.YELLOW + f"\nNow Push image {target_image}" + Color.END)
           subprocess.run(["docker", "push", target_image], check=True)
          
           # Чистим образы
           print(Color.YELLOW +f"\nDocker delete images: {target_image} AND {source_image}" + Color.END)
           subprocess.run(["docker", "image", "rm", source_image], check=True)
           subprocess.run(["docker", "image", "rm", target_image], check=True)

def main():
   while True:
       print(Color.DARKCYAN + '\n--------------------------------' + Color.END)
       print(Color.YELLOW + 'Выберите вариант: ' + Color.END)
       print(Color.GREEN + '1. ' + Color.END + 'Перенос RAW репы')
       print(Color.GREEN + '2. ' + Color.END + 'Перенос DOCKER репы')
       print(Color.GREEN + '3. ' + Color.END + 'Выход')
       choice = input('\nВведите номер варианта: ')
       if choice == '1':
           if not os.path.exists(DOWNLOAD_DIR):
                os.makedirs(DOWNLOAD_DIR)
           artifacts = get_artifacts_from_nexus()
           # Вывод json ответа для диагностики
           print(artifacts)
           for artifact in artifacts:
               download_artifact(artifact)
       elif choice == '2':
           images = get_docker_images_from_nexus()
           # Вывод json ответа для диагностики
           print(images)
           migrate_docker_images(images)
          
       elif choice == '3':
           print(Color.BLUE + '\nУдачи DevoPES...:)' + Color.END)
           break
       else:
           print(Color.BLUE + '\nНекорректный вариант, попробуй снова!' + Color.END) 
      
if __name__ == "__main__":
   main()
