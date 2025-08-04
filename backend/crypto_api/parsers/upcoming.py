#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
import os


class CryptoRankUpcomingParser:
    """
    Парсер CryptoRank для upcoming ICO проектов
    Сохраняет данные в таблицу cryptorank_upcoming
    """

    def __init__(self):
        self.upcoming_url = "https://cryptorank.io/upcoming-ico"

        # Настройки БД
        self.db_config = {
            'host': os.environ.get('DB_HOST', 'localhost'),
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

        # Базовые настройки
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-images')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(5)

        print("   ✅ Браузер готов")
        return driver

    def extract_name_from_url(self, url):
        """Извлекает название проекта из URL"""
        try:
            slug = url.split('/ico/')[-1].split('?')[0]
            name = slug.replace('-', ' ').title()
            return name
        except:
            return "Unknown Project"

    def extract_name_and_symbol_from_element(self, element):
        """Извлекает название и символ из элемента"""
        try:
            text = element.text.strip()

            # Если есть \n - символ после переноса
            if '\n' in text:
                parts = text.split('\n')
                name = parts[0].strip()
                symbol = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
                return name, symbol

            # Иначе просто текст
            return text, None

        except:
            return element.text.strip() if element.text else "Unknown", None

    def convert_date_format(self, date_text):
        """Конвертирует дату из формата '22 Jul' в 'YYYY-MM-DD'"""
        if not date_text or date_text == 'TBA':
            return None, date_text

        try:
            # Словарь месяцев
            months = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
            }

            # Парсим дату формата "22 Jul" или "1 Aug"
            parts = date_text.strip().split()
            if len(parts) >= 2:
                day = parts[0].zfill(2)  # Добавляем 0 если нужно: 1 -> 01
                month_text = parts[1][:3]  # Берем первые 3 символа месяца

                if month_text in months:
                    month = months[month_text]
                    year = '2025'  # Предполагаем текущий год
                    return f"{year}-{month}-{day}", date_text

            return None, date_text  # Возвращаем None если не смогли распарсить

        except Exception:
            return None, date_text

    def clean_text(self, text):
        """Очистка текста"""
        if not text:
            return None

        text = text.strip()

        # Пустые значения
        if not text or text in ['-', '–', 'N/A', 'TBD', '']:
            return None

        return text

    def merge_arrays(self, existing_array, new_array):
        """
        Умное объединение массивов investors/launchpad
        Если новый массив пустой - оставляем существующий
        Если есть новые данные - объединяем без дублей
        """
        if not new_array:  # Если новый массив пустой
            return existing_array if existing_array else []

        if not existing_array:  # Если существующий массив пустой
            return new_array

        # Объединяем массивы без дублей
        combined = list(existing_array)
        for item in new_array:
            if item not in combined:
                combined.append(item)

        return combined

    def parse_table(self):
        """Парсинг таблицы"""
        driver = self.setup_driver(headless=True)

        try:
            print(f"🌐 Загрузка: {self.upcoming_url}")
            driver.get(self.upcoming_url)
            time.sleep(3)

            # Прокрутка
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Извлечение проектов
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
            driver.quit()

    def extract_projects(self, driver):
        """Извлечение проектов"""
        print("   🔍 Поиск проектов...")

        projects = []
        seen_urls = set()

        try:
            # Находим все ссылки на проекты
            ico_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/ico/')]")
            print(f"      ✓ Найдено ссылок: {len(ico_links)}")

            for link in ico_links:
                try:
                    url = link.get_attribute('href')

                    # Проверяем URL
                    if not self.is_valid_ico_url(url) or url in seen_urls:
                        continue

                    seen_urls.add(url)

                    # Извлекаем данные
                    project_data = self.extract_project_data(link, url, len(projects) + 1)

                    if project_data:
                        projects.append(project_data)
                        name = project_data['project']['name']
                        symbol = project_data['project']['symbol']
                        when = project_data.get('when', 'N/A')
                        print(f"      ✅ {len(projects):2d}. {name} ({symbol or 'N/A'}) - {when}")

                except Exception:
                    continue

        except Exception as e:
            print(f"      ❌ Ошибка: {e}")

        return projects

    def extract_project_data(self, link, url, index):
        """Извлечение данных проекта из строки таблицы"""
        try:
            # Находим родительскую строку
            parent_row = self.find_table_row(link)
            if not parent_row:
                return None

            # Извлекаем название и символ из ссылки
            display_name, display_symbol = self.extract_name_and_symbol_from_element(link)

            # Если название адекватное - используем его, иначе из URL
            if display_name and len(display_name) > 3 and display_name != "Unknown":
                final_name = display_name
                final_symbol = display_symbol
            else:
                final_name = self.extract_name_from_url(url)
                final_symbol = None

            # Читаем данные из ячеек таблицы
            cells = parent_row.find_elements(By.TAG_NAME, "td")

            project_data = {
                'row_index': index,
                'project': {
                    'name': final_name,
                    'symbol': final_symbol,
                    'url': url
                },
                'investors': [],
                'launchpad': []
            }

            # Умное извлечение данных - определяем что есть что по содержимому
            for i, cell in enumerate(cells[1:], 1):  # Пропускаем первую колонку (название)
                text = self.clean_text(cell.text)
                if not text:
                    continue

                # Определяем тип данных по содержимому
                if text in ['IDO', 'ICO', 'IEO', 'Private', 'Pre-sale', 'KOL'] or any(
                        t in text for t in ['IDO', 'ICO', 'Private']):
                    project_data['type'] = text
                elif text.startswith('$') and any(c in text for c in 'KMB'):
                    # Денежная сумма
                    if 'initial_cap' not in project_data:
                        project_data['initial_cap'] = text
                    else:
                        project_data['ido_raise'] = text
                elif any(platform in text for platform in
                         ['Seedify', 'Polkastarter', 'Spores Network', 'AITECH PAD', 'Binance Wallet', 'Coinlist',
                          'FireStarter', 'TrustPad', 'Koistarter', 'TruePNL', 'WeWay', 'ChainGPT Pad', 'Agentlauncher',
                          'StarLaunch', 'LEGION', 'Tokensoft', 'BinStarter', 'BullPerks', 'BSCS', 'RazrFi']):
                    # Не записываем в launchpad - оставляем пустым массивом
                    pass
                elif any(month in text for month in
                         ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov',
                          'Dec']) or text == 'TBA':
                    project_data['when'] = text
                elif text.isdigit():
                    project_data['moni_score'] = text

            # Удаляем пустые поля, но сохраняем investors и launchpad
            project_data = {k: v for k, v in project_data.items() if v or k in ['investors', 'launchpad']}

            # Не собираем данные если дата TBA
            if project_data.get('when') == 'TBA':
                return None

            return project_data if len(project_data) >= 3 else None

        except Exception:
            return None

    def find_table_row(self, link):
        """Поиск родительской строки таблицы"""
        try:
            # Ищем родительский tr или div
            ancestors = [
                "./ancestor::tr[1]",
                "./ancestor::div[contains(@class, 'row')][1]",
                "./ancestor::div[position()<=3]"
            ]

            for ancestor_xpath in ancestors:
                try:
                    parent = link.find_element(By.XPATH, ancestor_xpath)
                    if parent and len(parent.text.strip()) > 20:
                        return parent
                except:
                    continue

            return None
        except:
            return None

    def is_valid_ico_url(self, url):
        """Проверка валидности URL"""
        if not url or '/ico/' not in url:
            return False

        exclude = ['/categories/', '/exchanges/', '/coins/', '/price/']
        return not any(ex in url for ex in exclude)

    def save_to_database(self, projects):
        """Сохраняет проекты в таблицу cryptorank_upcoming"""
        if not projects:
            print("❌ Нет данных для сохранения")
            return

        conn = self.get_db_connection()
        if not conn:
            return

        cursor = conn.cursor()
        saved_count = 0
        updated_count = 0
        skipped_count = 0

        print("\n💾 Сохранение в БД...")

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
                    SELECT id, updated_at, investors, launchpad FROM cryptorank_upcoming 
                    WHERE project_url = %s
                """, (url,))

                existing = cursor.fetchone()

                if existing:
                    # Обновляем существующую запись
                    existing_id = existing[0]
                    existing_investors = existing[2] if existing[2] else []
                    existing_launchpad = existing[3] if existing[3] else []

                    # Умно объединяем массивы
                    new_investors = project.get('investors', [])
                    new_launchpad = project.get('launchpad', [])

                    merged_investors = self.merge_arrays(existing_investors, new_investors)
                    merged_launchpad = self.merge_arrays(existing_launchpad, new_launchpad)

                    cursor.execute("""
                        UPDATE cryptorank_upcoming SET
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
                            row_index = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (
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
                        project.get('row_index'),
                        existing_id
                    ))

                    updated_count += 1

                    # Показываем что изменилось
                    investors_changed = len(merged_investors) > len(existing_investors)
                    launchpad_changed = len(merged_launchpad) > len(existing_launchpad)
                    change_info = ""
                    if investors_changed:
                        change_info += f" [+{len(merged_investors) - len(existing_investors)} investors]"
                    if launchpad_changed:
                        change_info += f" [+{len(merged_launchpad) - len(existing_launchpad)} launchpad]"

                    print(f"  🔄 Обновлен: {project_info.get('name')} ({project_info.get('symbol')}){change_info}")

                else:
                    # Вставляем новую запись
                    cursor.execute("""
                        INSERT INTO cryptorank_upcoming (
                            row_index, project_name, project_symbol, project_url,
                            project_type, initial_cap, ido_raise, launch_date,
                            launch_date_original, moni_score, investors, launchpad
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                    """, (
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
                    ))

                    saved_count += 1
                    print(f"  ✅ Добавлен: {project_info.get('name')} ({project_info.get('symbol')})")

            conn.commit()

        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

        print(f"\n📊 Итоги сохранения:")
        print(f"  ✅ Новых проектов: {saved_count}")
        print(f"  🔄 Обновлено: {updated_count}")
        print(f"  ⏭️ Пропущено: {skipped_count}")

    def get_database_stats(self):
        """Получает статистику из БД"""
        conn = self.get_db_connection()
        if not conn:
            return

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            print("\n📊 Статистика базы данных:")

            # Общая статистика
            cursor.execute("SELECT * FROM get_upcoming_stats()")
            stats = cursor.fetchone()

            if stats:
                print(f"  📈 Всего проектов: {stats['total_projects']}")
                print(f"  ✅ Активных: {stats['active_projects']}")
                print(f"  📅 На этой неделе: {stats['this_week']}")
                print(f"  🗓️ В этом месяце: {stats['this_month']}")
                print(f"  💰 С капитализацией: {stats['with_initial_cap']}")
                if stats['avg_moni_score']:
                    print(f"  ⭐ Средний Moni Score: {stats['avg_moni_score']}")

            # Ближайшие проекты
            cursor.execute("SELECT * FROM upcoming_soon LIMIT 5")
            upcoming = cursor.fetchall()

            if upcoming:
                print(f"\n🚀 Ближайшие запуски:")
                for project in upcoming:
                    days = project['days_until_launch']
                    print(f"  • {project['project_name']} ({project['project_symbol']}) - через {days:.0f} дней")

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


def main():
    """Главная функция"""
    print("🚀 ПАРСЕР UPCOMING ICO ПРОЕКТОВ")
    print("=" * 50)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Сохранение в таблицу: cryptorank_upcoming")
    print("=" * 50)

    parser = CryptoRankUpcomingParser()

    # Запускаем парсинг
    result = parser.parse_table()

    if result:
        # Сохраняем в БД
        parser.save_to_database(result['projects'])

        # Показываем статистику
        parser.get_database_stats()

        # Опционально сохраняем JSON
        # parser.save_results(result)

        print(f"\n✅ Готово!")
        print(f"📊 Обработано проектов: {result.get('total_projects', 0)}")
        print(f"🎯 Только проекты с конкретными датами (без TBA)")
    else:
        print("❌ Парсинг не удался")

    print("=" * 50)
