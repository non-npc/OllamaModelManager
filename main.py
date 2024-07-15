import eel
import scrapy
from scrapy.crawler import CrawlerProcess
import sqlite3
import re
import os
import subprocess
import datetime
from urllib.parse import urlparse

eel.init('web')

class OllamaSpider(scrapy.Spider):
    name = 'ollama_spider'
    start_urls = ['https://ollama.com/library/']
    LOG_ENABLED = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = sqlite3.connect('myollama.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ollama_models
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             model_name TEXT,
             model_description TEXT,
             model_pulls INTEGER,
             model_last_updated TEXT,
             model_archived INTEGER DEFAULT 0,
             model_versions TEXT,
             latest_version TEXT)
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS last_update
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             update_time TEXT)
        ''')
        
    def parse(self, response):
        for model in response.css('div#repo li'):
            model_url = model.css('a::attr(href)').get()
            yield response.follow(model_url, self.parse_model)

    def parse_model(self, response):
        url_path = urlparse(response.url).path
        model_name = url_path.split('/')[-1]

        model_archived = 1 if response.css('span:contains("Archive")').get() else 0

        model_description = response.css('h2.break-words::text').get()
        model_description = model_description.strip() if model_description else ''

        pulls_attr = response.css('span[title$="pulls"]::attr(title)').get()
        model_pulls = 0
        if pulls_attr:
            pulls_match = re.search(r'(\d+)\s+pulls', pulls_attr)
            if pulls_match:
                model_pulls = int(pulls_match.group(1))

        model_last_updated = response.css('span#updateMessage::text').get()
        if model_last_updated:
            model_last_updated = model_last_updated.replace('Updated ', '').strip()

        version_elements = response.css('div#primary-tags .flex.space-x-2.items-center')
        versions = set()
        latest_version = None
        for elem in version_elements:
            version = elem.css('span[title]::text').get().strip()
            is_latest = elem.css('span:contains("latest")').get() is not None
            if is_latest:
                latest_version = version
            if version.lower() != 'latest':
                versions.add(version)

        versions = sorted(list(versions))
        if latest_version and latest_version in versions:
            versions.remove(latest_version)
            versions.insert(0, latest_version)
        
        model_versions = ', '.join(versions)

        self.cursor.execute('''
            INSERT INTO ollama_models 
            (model_name, model_description, model_pulls, model_last_updated, model_archived, model_versions, latest_version)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (model_name, model_description, model_pulls, model_last_updated, model_archived, model_versions, latest_version))
        
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("INSERT INTO last_update (update_time) VALUES (?)", (current_time,))
        
        self.conn.commit()

    def closed(self, reason):
        self.conn.close()

class OllamaGUI:
    @staticmethod
    @eel.expose
    def load_data():
        conn = sqlite3.connect('myollama.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ollama_models
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             model_name TEXT,
             model_description TEXT,
             model_pulls INTEGER,
             model_last_updated TEXT,
             model_archived INTEGER DEFAULT 0,
             model_versions TEXT,
             latest_version TEXT)
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS last_update
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             update_time TEXT)
        ''')
        
        cursor.execute("SELECT update_time FROM last_update ORDER BY id DESC LIMIT 1")
        last_update = cursor.fetchone()
        last_update_time = last_update[0] if last_update else "Never"
        
        cursor.execute('SELECT * FROM ollama_models ORDER BY model_last_updated ASC')
        rows = cursor.fetchall()
        conn.close()

        local_models = OllamaGUI.get_local_models()

        prepared_rows = []
        installed_rows = []
        for row in rows:
            is_installed = any(row[1] + ":" in model for model in local_models)
            if is_installed:
                installed_rows.append((row, True))
            else:
                prepared_rows.append((row, False))
        
        prepared_rows = installed_rows + prepared_rows

        return prepared_rows, local_models, last_update_time

    @staticmethod
    @eel.expose
    def get_local_models():
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            models = [line.split()[0] for line in result.stdout.split('\n')[1:] if line]
            return models
        except Exception:
            return []

    @staticmethod
    @eel.expose
    def install_model(model_name, version):
        try:
            subprocess.run(['ollama', 'pull', f"{model_name}:{version}"], check=True)
            return True, f"Installed {model_name}:{version}"
        except subprocess.CalledProcessError:
            return False, f"Failed to install {model_name}:{version}"

    @staticmethod
    @eel.expose
    def uninstall_model(model_name, version):
        try:
            subprocess.run(['ollama', 'rm', f"{model_name}:{version}"], check=True)
            return True, f"Uninstalled {model_name}:{version}"
        except subprocess.CalledProcessError:
            return False, f"Failed to uninstall {model_name}:{version}"

    @staticmethod
    @eel.expose
    def update_database():
        if os.path.exists('myollama.db'):
            os.remove('myollama.db')
        process = CrawlerProcess()
        process.crawl(OllamaSpider)
        process.start()
        
        conn = sqlite3.connect('myollama.db')
        cursor = conn.cursor()
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO last_update (update_time) VALUES (?)", (current_time,))
        conn.commit()
        conn.close()
        
        return "Database updated", current_time

def main():
    if not os.path.exists('myollama.db'):
        process = CrawlerProcess()
        process.crawl(OllamaSpider)
        process.start()

    eel.start('index.html', size=(1000, 600))

if __name__ == '__main__':
    main()