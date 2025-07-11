from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit, QStackedWidget, QWidget, QHBoxLayout, QMessageBox, QApplication)
from PyQt5.QtCore import Qt
import webbrowser
import requests
import os
import json

GITHUB_CREDS_FILE = '.github_creds'

class GitHubWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Мастер настройки GitHub')
        self.setFixedSize(500, 350)
        self.layout = QVBoxLayout(self)
        self.stack = QStackedWidget(self)
        self.layout.addWidget(self.stack)
        self.steps = []
        self.init_steps()
        self.current_step = 0
        self.show_step(0)

    def init_steps(self):
        # Шаг 1: Создание репозитория
        page1 = QWidget()
        l1 = QVBoxLayout(page1)
        l1.addWidget(QLabel('1. Создайте новый приватный репозиторий на GitHub для хранения сохранений.'))
        repo_btn = QPushButton('Открыть GitHub')
        repo_btn.clicked.connect(lambda: webbrowser.open('https://github.com/new'))
        l1.addWidget(repo_btn)
        next1 = QPushButton('Далее')
        next1.clicked.connect(lambda: self.show_step(1))
        l1.addWidget(next1, alignment=Qt.AlignRight)
        self.stack.addWidget(page1)
        self.steps.append(page1)

        # Шаг 2: Получение токена
        page2 = QWidget()
        l2 = QVBoxLayout(page2)
        l2.addWidget(QLabel('2. Получите Personal Access Token с правами repo.'))
        token_btn = QPushButton('Открыть страницу токенов')
        token_btn.clicked.connect(lambda: webbrowser.open('https://github.com/settings/tokens/new?scopes=repo&description=DS3CloudSave'))
        l2.addWidget(token_btn)
        next2 = QPushButton('Далее')
        next2.clicked.connect(lambda: self.show_step(2))
        l2.addWidget(next2, alignment=Qt.AlignRight)
        self.stack.addWidget(page2)
        self.steps.append(page2)

        # Шаг 3: Ввод данных
        page3 = QWidget()
        l3 = QVBoxLayout(page3)
        l3.addWidget(QLabel('3. Вставьте ссылку на репозиторий и токен.'))
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText('https://github.com/username/repo.git')
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText('Personal Access Token')
        self.token_input.setEchoMode(QLineEdit.Password)
        paste_btn = QPushButton('Вставить из буфера')
        paste_btn.clicked.connect(self.paste_from_clipboard)
        l3.addWidget(QLabel('Ссылка на репозиторий:'))
        l3.addWidget(self.repo_input)
        l3.addWidget(QLabel('Токен:'))
        l3.addWidget(self.token_input)
        l3.addWidget(paste_btn)
        next3 = QPushButton('Далее')
        next3.clicked.connect(self.check_github)
        l3.addWidget(next3, alignment=Qt.AlignRight)
        self.stack.addWidget(page3)
        self.steps.append(page3)

        # Шаг 4: Проверка
        page4 = QWidget()
        l4 = QVBoxLayout(page4)
        self.check_label = QLabel('Проверка данных...')
        l4.addWidget(self.check_label)
        self.check_next_btn = QPushButton('Готово')
        self.check_next_btn.clicked.connect(self.accept)
        l4.addWidget(self.check_next_btn, alignment=Qt.AlignRight)
        self.stack.addWidget(page4)
        self.steps.append(page4)

    def show_step(self, idx):
        self.current_step = idx
        self.stack.setCurrentIndex(idx)

    def paste_from_clipboard(self):
        cb = QApplication.clipboard()
        text = cb.text()
        if 'github.com' in text:
            self.repo_input.setText(text)
        else:
            self.token_input.setText(text)

    def check_github(self):
        repo_url = self.repo_input.text().strip()
        token = self.token_input.text().strip()
        if not repo_url or not token:
            QMessageBox.warning(self, 'Ошибка', 'Пожалуйста, введите ссылку и токен.')
            return
        self.show_step(3)
        self.check_label.setText('Проверка данных...')
        QApplication.processEvents()
        # Проверка доступа к репозиторию через GitHub API
        try:
            repo_path = repo_url.replace('https://github.com/', '').replace('.git', '')
            api_url = f'https://api.github.com/repos/{repo_path}'
            r = requests.get(api_url, headers={'Authorization': f'token {token}'})
            if r.status_code == 200:
                # Пробуем тестовый push (создать/обновить файл)
                self.check_label.setText('Доступ подтверждён. Сохраняю настройки...')
                self.save_creds(repo_url, token)
                self.check_next_btn.setEnabled(True)
            else:
                self.check_label.setText('Ошибка доступа: проверьте токен и ссылку.')
                self.check_next_btn.setEnabled(False)
        except Exception as e:
            self.check_label.setText(f'Ошибка: {e}')
            self.check_next_btn.setEnabled(False)

    def save_creds(self, repo_url, token):
        creds = {'repo_url': repo_url, 'token': token}
        with open(GITHUB_CREDS_FILE, 'w') as f:
            json.dump(creds, f)

    @staticmethod
    def load_creds():
        if os.path.exists(GITHUB_CREDS_FILE):
            with open(GITHUB_CREDS_FILE, 'r') as f:
                return json.load(f)
        return None 