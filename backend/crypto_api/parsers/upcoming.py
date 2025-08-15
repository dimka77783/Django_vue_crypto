#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime


# 🔥 УСТАНАВЛИВАЕМ ПУТЬ ДЛЯ SELENIUM САМОЙ ПЕРВОЙ СТРОКОЙ
os.environ['SELENIUM_CACHE_PATH'] = '/tmp/selenium'
os.makedirs('/tmp/selenium', exist_ok=True)


class CryptoRankUpcomingParser:
    """
    Парсер CryptoRank для upcoming ICO проектов
    Сохраняет данные в таблицу cryptorank_upcoming
    """

    def __init__(self):
        self.upcoming_url = "https://cryptorank.io/upcoming-ico"

        # Настройки БД
        self.db_config = {
            'host': os.environ.get('DB_HOST', 'postgres'),
            'port': os.environ.get('DB_PORT', '5432'),
            'database': os.environ.get('DB_NAME', 'crypto_db'),
            'user': os.environ.get('DB_USER', 'crypto_user'),
            'password': os.environ.get('DB_PASSWORD', 'crypto_password')
        }

    def get_db_connection(self):
        """Создает подключение к БД"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            return None

    def setup_driver(self, headless=True):
        """Настройка браузера"""
        print("🔧 Настройка браузера...")
        options = webdriver.ChromeOptions()

        if headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        # Уникальная директория профиля
        user_data_dir = f"/tmp/chrome_profile_{os.getpid()}"
        os.makedirs(user_data_dir, exist_ok=True)
        options.add_argument(f'--user-data-dir={user_data_dir}')

        try:
            driver = webdriver.Chrome(options=options)
            driver.implicitly_wait(10)
            print("✅ Браузер готов")
            return driver
        except Exception as e:
            print(f"❌ Ошибка запуска браузера: {e}")
            return None

    def convert_date_format(self, when_text):
        """Конвертирует '14 Aug' → '2025-08-14'"""
        if not when_text or 'TBA' in when_text.upper():
            return None, when_text

        try:
            from datetime import datetime as dt
            current_year = dt.now().year
            full_date_str = f"{when_text} {current_year}"
            parsed_date = dt.strptime(full_date_str, '%d %b %Y')
            return parsed_date.date(), when_text
        except Exception as e:
            print(f"⚠️ Не удалось распарсить дату: {when_text}")
            return None, when_text

    def extract_projects(self, driver):
        """Извлекает проекты из таблицы"""
        print("🔍 Поиск проектов...")
        projects = []

        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "tr[role='row']")
            print(f" ✓ Найдено строк: {len(rows)}")

            for idx, row in enumerate(rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 7:
                        continue

                    # Проект и URL
                    project_cell = cells[1]
                    link = project_cell.find_element(By.TAG_NAME, "a")
                    project_name = link.text.strip()
                    project_url = link.get_attribute("href")

                    # Символ
                    symbol_cell = cells[2]
                    project_symbol = symbol_cell.text.strip()

                    # Тип
                    type_cell = cells[3]
                    project_type = type_cell.text.strip()

                    # Капитализация
                    cap_cell = cells[4]
                    initial_cap = cap_cell.text.strip()

                    # IDO Raise
                    ido_cell = cells[5]
                    ido_raise = ido_cell.text.strip() if ido_cell.text.strip() != '-' else None

                    # Дата
                    when_cell = cells[6]
                    when_text = when_cell.text.strip()

                    # Moni Score
                    moni_cell = cells[7]
                    moni_score = moni_cell.text.strip() if moni_cell.text.strip() != '-' else None

                    # Собираем данные
                    project_data = {
                        'row_index': idx + 1,
                        'project': {
                            'name': project_name,
                            'symbol': project_symbol,
                            'url': project_url
                        },
                        'type': project_type,
                        'initial_cap': initial_cap,
                        'ido_raise': ido_raise,
                        'when': when_text,
                        'moni_score': moni_score,
                        'investors': [],
                        'launchpad': []
                    }

                    if project_url and '/ico/' in project_url:
                        projects.append(project_data)

                except Exception as e:
                    print(f"⚠️ Ошибка парсинга строки: {e}")
                    continue

            print(f"✅ Найдено проектов: {len(projects)}")
            return projects

        except Exception as e:
            print(f"❌ Ошибка извлечения проектов: {e}")
            return []

    def merge_lists(self, existing, new_list):
        """Объединяет два списка без дубликатов"""
        combined = existing.copy() if existing else []
        for item in new_list:
            if item not in combined:
                combined.append(item)
        return combined

    def save_to_database(self, projects):
        """Сохраняет проекты в таблицу cryptorank_upcoming"""
        if not projects:
            print("❌ Нет данных для сохранения")
            return

        conn = self.get_db_connection()
        if not conn:
            return

        cursor = conn.cursor()
        new_count = 0
        updated_count = 0
        skipped_count = 0

        print("💾 Сохранение в БД...")
        try:
            for project in projects:
                project_info = project.get('project', {})
                url = project_info.get('url')
                if not url:
                    skipped_count += 1
                    continue

                # Конвертируем дату
                when_text = project.get('when')
                launch_date, launch_date_original = self.convert_date_format(when_text)

                # Проверяем существование по URL
                cursor.execute("""
                    SELECT id, updated_at, investors, launchpad 
                    FROM cryptorank_upcoming 
                    WHERE project_url = %s
                """, (url,))
                existing = cursor.fetchone()

                # Собираем данные
                data_tuple = (
                    project.get('row_index'),
                    project_info.get('name'),
                    project_info.get('symbol'),
                    url,
                    project.get('type'),
                    project.get('initial_cap'),
                    project.get('ido_raise'),
                    launch_date,
                    launch_date_original,
                    project.get('moni_score'),
                    json.dumps(project.get('investors', [])),
                    json.dumps(project.get('launchpad', []))
                )

                if existing:
                    # Обновляем существующую запись
                    existing_id = existing[0]
                    existing_investors = existing[2] if existing[2] else []
                    existing_launchpad = existing[3] if existing[3] else []

                    # Слияние инвесторов и launchpad
                    merged_investors = self.merge_lists(existing_investors, project.get('investors', []))
                    merged_launchpad = self.merge_lists(existing_launchpad, project.get('launchpad', []))

                    cursor.execute("""
                        UPDATE cryptorank_upcoming SET
                            row_index = %s,
                            project_name = %s,
                            project_symbol = %s,
                            project_type = %s,
                            initial_cap = %s,
                            ido_raise = %s,
                            launch_date = %s,
                            launch_date_original = %s,
                            moni_score = %s,
                            investors = %s::jsonb,
                            launchpad = %s::jsonb,
                            updated_at = CURRENT_TIMESTAMP,
                            parsed_at = CURRENT_TIMESTAMP
                        WHERE project_url = %s
                    """, (
                        project.get('row_index'),
                        project_info.get('name'),
                        project_info.get('symbol'),
                        project.get('type'),
                        project.get('initial_cap'),
                        project.get('ido_raise'),
                        launch_date,
                        launch_date_original,
                        project.get('moni_score'),
                        json.dumps(merged_investors),
                        json.dumps(merged_launchpad),
                        url
                    ))
                    updated_count += 1
                else:
                    # Вставляем новую запись
                    cursor.execute("""
                        INSERT INTO cryptorank_upcoming (
                            row_index, project_name, project_symbol, project_url,
                            project_type, initial_cap, ido_raise, launch_date,
                            launch_date_original, moni_score, investors, launchpad,
                            parsed_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, data_tuple)
                    new_count += 1

            conn.commit()
            print("📊 Итоги сохранения:")
            print(f" ✅ Новых проектов: {new_count}")
            print(f" 🔄 Обновлено: {updated_count}")
            print(f" ⏭️ Пропущено: {skipped_count}")

        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def get_database_stats(self):
        """Показывает статистику по БД"""
        conn = self.get_db_connection()
        if not conn:
            return

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            print("📊 Статистика базы данных:")
            cursor.execute("SELECT * FROM get_upcoming_stats()")
            stats = cursor.fetchone()
            if stats:
                print(f" 📈 Всего проектов: {stats['total_projects']}")
                print(f" ✅ Активных: {stats['active_projects']}")
                print(f" 📅 На этой неделе: {stats['this_week']}")
                print(f" 🗓️ В этом месяце: {stats['this_month']}")
                print(f" 💰 С капитализацией: {stats['with_initial_cap']}")
                if stats['avg_moni_score']:
                    print(f" ⭐ Средний Moni Score: {stats['avg_moni_score']}")

            # Ближайшие проекты
            cursor.execute("SELECT * FROM upcoming_soon LIMIT 5")
            upcoming = cursor.fetchall()
            if upcoming:
                print(f"🚀 Ближайшие запуски:")
                for project in upcoming:
                    days = project['days_until_launch']
                    print(f" • {project['project_name']} ({project['project_symbol']}) - через {days:.0f} дней")

        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
        finally:
            cursor.close()
            conn.close()

    def save_results(self, data, filename=None):
        """Сохранение результатов в JSON (опционально)"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'cryptorank_upcoming_{timestamp}.json'
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 JSON сохранен: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Ошибка сохранения JSON: {e}")
            return None

    def parse_table(self):
        """Парсинг таблицы"""
        driver = None
        try:
            print(f"🌐 Загрузка: {self.upcoming_url}")
            driver = self.setup_driver(headless=True)
            driver.get(self.upcoming_url)
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            projects = self.extract_projects(driver)

            result = {
                'source_url': self.upcoming_url,
                'parsed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_projects': len(projects),
                'projects': projects
            }
            print(f"✅ Парсинг завершен: {len(projects)} проектов")
            return result

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception as e:
                    print(f"⚠️ Ошибка при driver.quit(): {e}")
                # 🔥 Принудительное завершение процессов
                os.system("killall -q chrome chromedriver 2>/dev/null || true")
                print("🔒 Браузер закрыт (принудительно)")

    def main(self):
        """Главная функция парсера"""
        print("🚀 ПАРСЕР UPCOMING ICO ПРОЕКТОВ")
        print("=" * 60)
        print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Сохранение в таблицу: cryptorank_upcoming")
        print("=" * 60)

        parser = CryptoRankUpcomingParser()
        result = parser.parse_table()

        if result:
            parser.save_to_database(result['projects'])
            parser.get_database_stats()
            print(f"✅ Готово!")
            print(f"📊 Обработано проектов: {result.get('total_projects', 0)}")
        else:
            print("❌ Парсинг не удался")
        print("=" * 60)


# Глобальная функция для импорта
def main():
    """Точка входа для Django/Celery"""
    CryptoRankUpcomingParser().main()


# Для запуска из терминала
if __name__ == "__main__":
    main()