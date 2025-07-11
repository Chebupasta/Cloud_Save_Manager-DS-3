import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox, QInputDialog
import os
import shutil
from github_wizard import GitHubWizard
from ds3_paths import get_ds3_save_path
import requests
import json

BACKUP_DIR = 'backup'

def log_action(action, status, details=None):
    with open('log.txt', 'a', encoding='utf-8') as f:
        import datetime
        f.write(f"[{datetime.datetime.now()}] {action} | {status} | {details or ''}\n")

def find_all_ds3_saves():
    import sys, os
    saves = []
    if sys.platform.startswith('win'):
        appdata = os.getenv('APPDATA')
        base = os.path.join(appdata, 'DarkSoulsIII')
        if os.path.exists(base):
            for folder in os.listdir(base):
                slot = os.path.join(base, folder, 'DS30000.sl2')
                if os.path.isfile(slot):
                    saves.append(slot)
    else:
        home = os.path.expanduser('~')
        candidates = [
            os.path.join(home, '.steam/steam/steamapps/compatdata/374320/pfx/drive_c/users/steamuser/AppData/Roaming/DarkSoulsIII'),
            os.path.join(home, '.wine/drive_c/users/', os.getenv('USER', ''), 'AppData/Roaming/DarkSoulsIII'),
        ]
        for base in candidates:
            if os.path.exists(base):
                for folder in os.listdir(base):
                    slot = os.path.join(base, folder, 'DS30000.sl2')
                    if os.path.isfile(slot):
                        saves.append(slot)
    return saves

def get_default_branch(repo_path, token):
    api_url = f'https://api.github.com/repos/{repo_path}'
    r = requests.get(api_url, headers={'Authorization': f'token {token}'})
    if r.status_code == 200:
        return r.json().get('default_branch', 'main')
    return 'main'

class DS3CloudSaveManager(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('DS3 Cloud Save Manager')
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()
        layout.setSpacing(20)

        self.upload_btn = QPushButton('Выгрузить')
        self.download_btn = QPushButton('Загрузить')
        self.github_btn = QPushButton('Настроить GitHub')
        self.help_btn = QPushButton('Инструкция')

        self.upload_btn.setFixedHeight(50)
        self.download_btn.setFixedHeight(50)
        self.github_btn.setFixedHeight(50)
        self.help_btn.setFixedHeight(50)

        layout.addWidget(self.upload_btn)
        layout.addWidget(self.download_btn)
        layout.addWidget(self.github_btn)
        layout.addWidget(self.help_btn)

        self.setLayout(layout)

        # Пример обработчика кнопки
        self.upload_btn.clicked.connect(self.upload_save)
        self.download_btn.clicked.connect(self.download_save)
        self.github_btn.clicked.connect(self.setup_github)
        self.help_btn.clicked.connect(self.show_help)

    def get_save_path_with_choice(self):
        saves = find_all_ds3_saves()
        if not saves:
            return None
        if len(saves) == 1:
            return saves[0]
        # Выбор слота
        items = [os.path.dirname(s) for s in saves]
        idx, ok = QInputDialog.getItem(self, 'Выбор слота', 'Выберите слот сохранения:', items, 0, False)
        if ok:
            return saves[items.index(idx)]
        return None

    def upload_save(self):
        save_path = self.get_save_path_with_choice()
        if not save_path or not os.path.isfile(save_path):
            log_action('upload', 'fail', 'save not found')
            QMessageBox.warning(self, 'Ошибка', 'Файл сохранения DS3 не найден!')
            return
        creds = GitHubWizard.load_creds()
        if not creds:
            log_action('upload', 'fail', 'no creds')
            QMessageBox.warning(self, 'Ошибка', 'Сначала настройте GitHub!')
            return
        repo_url = creds['repo_url']
        token = creds['token']
        repo_path = repo_url.replace('https://github.com/', '').replace('.git', '')
        branch = get_default_branch(repo_path, token)
        api_url = f'https://api.github.com/repos/{repo_path}/contents/DS30000.sl2'
        with open(save_path, 'rb') as f:
            content = f.read()
        log_action('upload', 'debug', f'upload size: {len(content)}')
        if len(content) == 0:
            log_action('upload', 'fail', 'file is empty')
            QMessageBox.warning(self, 'Ошибка', 'Файл сохранения пустой!')
            return
        import base64
        b64_content = base64.b64encode(content).decode('utf-8')
        # Получаем SHA, если файл уже есть
        r = requests.get(api_url, headers={'Authorization': f'token {token}'})
        sha = r.json().get('sha') if r.status_code == 200 else None
        data = {
            'message': 'DS3 save upload',
            'content': b64_content,
            'branch': branch,
        }
        if sha:
            data['sha'] = sha
        r = requests.put(api_url, headers={'Authorization': f'token {token}'}, data=json.dumps(data))
        if r.status_code in (200, 201):
            log_action('upload', 'success')
            QMessageBox.information(self, 'Успех', 'Сохранение успешно выгружено на GitHub!')
        else:
            log_action('upload', 'fail', r.text)
            QMessageBox.warning(self, 'Ошибка', f'Ошибка загрузки: {r.text}')

    def download_save(self):
        save_path = self.get_save_path_with_choice()
        if not save_path:
            log_action('download', 'fail', 'save path not found')
            QMessageBox.warning(self, 'Ошибка', 'Папка сохранений DS3 не найдена!')
            return
        creds = GitHubWizard.load_creds()
        if not creds:
            log_action('download', 'fail', 'no creds')
            QMessageBox.warning(self, 'Ошибка', 'Сначала настройте GitHub!')
            return
        repo_url = creds['repo_url']
        token = creds['token']
        repo_path = repo_url.replace('https://github.com/', '').replace('.git', '')
        branch = get_default_branch(repo_path, token)
        api_url = f'https://api.github.com/repos/{repo_path}/contents/DS30000.sl2?ref={branch}'
        r = requests.get(api_url, headers={'Authorization': f'token {token}'})
        if r.status_code == 200:
            json_data = r.json()
            # Если есть download_url — качаем по нему
            if 'download_url' in json_data and json_data['download_url']:
                file_resp = requests.get(json_data['download_url'])
                content = file_resp.content
            else:
                import base64
                content = base64.b64decode(json_data['content'])
            log_action('download', 'debug', f'downloaded size: {len(content)}')
            if len(content) == 0:
                log_action('download', 'fail', 'downloaded file is empty')
                QMessageBox.warning(self, 'Ошибка', 'Загруженный файл пустой!')
                return
            # Бэкапим текущее сохранение
            os.makedirs(BACKUP_DIR, exist_ok=True)
            if os.path.isfile(save_path):
                shutil.copy2(save_path, os.path.join(BACKUP_DIR, 'DS30000_backup.sl2'))
            with open(save_path, 'wb') as f:
                f.write(content)
            QMessageBox.information(self, 'Успех', 'Сохранение успешно загружено из GitHub!')
            log_action('download', 'success')
        else:
            log_action('download', 'fail', r.text)
            QMessageBox.warning(self, 'Ошибка', f'Ошибка загрузки: {r.text}')

    def setup_github(self):
        dlg = GitHubWizard(self)
        if dlg.exec_() == dlg.Accepted:
            QMessageBox.information(self, 'Готово', 'GitHub успешно настроен!')

    def show_help(self):
        text = (
            'DS3 Cloud Save Manager — резервное копирование и восстановление сохранений Dark Souls 3 через GitHub.\n\n'
            '1. Нажмите “Настроить GitHub” и следуйте шагам мастера.\n'
            '2. Создайте приватный репозиторий и получите Personal Access Token.\n'
            '3. Введите данные, дождитесь проверки.\n'
            '4. Для выгрузки сохранения нажмите “Выгрузить”.\n'
            '5. Для восстановления — “Загрузить”.\n\n'
            'Ссылки:\n'
            '• Создать репозиторий: https://github.com/new\n'
            '• Получить токен: https://github.com/settings/tokens/new?scopes=repo\n\n'
            'Все действия сопровождаются уведомлениями.\n'
            'Если возникла ошибка — внимательно проверьте токен и ссылку на репозиторий.\n'
            'Ваш токен хранится только локально и не публикуется.'
        )
        QMessageBox.information(self, 'Инструкция', text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DS3CloudSaveManager()
    window.show()
    sys.exit(app.exec_()) 