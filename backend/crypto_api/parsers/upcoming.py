#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import time
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime  # ✅ Исправлено: добавлен импорт

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
            if '\n' in text:
                parts = text.split('\n')
                name = parts[0].strip()
                symbol = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
                return name, symbol
            return text, None
        except:
            return element.text.strip() if element.text else "Unknown", None

    def convert_date_format(self, date_text):
        """Конвертирует дату из формата '22 Jul' в 'YYYY-MM-DD'"""
        if not date_text or date_text == 'TBA':
            return None, date_text
        try:
            months = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
            }
            parts = date_text.strip().split()
            if len(parts) >= 2:
                day = parts[0].zfill(2)
                month_text = parts[1][:3]
                if month_text in months:
                    month = months[month_text]
                    year = '2025'
                    return f"{year}-{month}-{day}", date_text
            return None, date_text
        except Exception:
            return None, date_text

    def clean_text(self, text):
        """Очистка текста"""
        if not text:
            return None
        text = text.strip()
        if not text or text in ['-', '–', 'N/A', 'TBD', '']:
            return None
        return text

    def merge_arrays(self, existing_array, new_array):
        if not new_array:
            return existing_array if existing_array else []
        if not existing_array:
            return new_array
        combined = list(existing_array)
        for item in new_array:
            if item not in combined:
                combined.append(item)
        return combined

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

    def extract_projects(self, driver):
        print("   🔍 Поиск проектов...")
        projects = []
        seen_urls = set()
        try:
            ico_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/ico/')]")
            print(f"      ✓ Найдено ссылок: {len(ico_links)}")
            for link in ico_links:
                try:
                    url = link.get_attribute('href')
                    if not self.is_valid_ico_url(url) or url in seen_urls:
                        continue
                    seen_urls.add(url)
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
        try:
            parent_row = self.find_table_row(link)
            if not parent_row:
                return None
            display_name, display_symbol = self.extract_name_and_symbol_from_element(link)
            if display_name and len(display_name) > 3 and display_name != "Unknown":
                final_name = display_name
                final_symbol = display_symbol
            else:
                final_name = self.extract_name_from_url(url)
                final_symbol = None
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
            for i, cell in enumerate(cells[1:], 1):
                text = self.clean_text(cell.text)
                if not text:
                    continue
                if text in ['IDO', 'ICO', 'IEO', 'Private', 'Pre-sale', 'KOL'] or any(t in text for t in ['IDO', 'ICO', 'Private']):
                    project_data['type'] = text
                elif text.startswith('$') and any(c in text for c in 'KMB'):
                    if 'initial_cap' not in project_data:
                        project_data['initial_cap'] = text
                    else:
                        project_data['ido_raise'] = text
                elif any(month in text for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']) or text == 'TBA':
                    project_data['when'] = text
                elif text.isdigit():
                    project_data['moni_score'] = text
            project_data = {k: v for k, v in project_data.items() if v or k in ['investors', 'launchpad']}
            if project_data.get('when') == 'TBA':
                return None
            return project_data if len(project_data) >= 3 else None
        except Exception:
            return None

    def find_table_row(self, link):
        try:
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
        if not url or '/ico/' not in url:
            return False
        exclude = ['/categories/', '/exchanges/', '/coins/', '/price/']
        return not any(ex in url for ex in exclude)

    def save_to_database(self, projects):
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
                when_text = project.get('when')
                launch_date, launch_date_original = self.convert_date_format(when_text)
                cursor.execute("""
                    SELECT id, updated_at, investors, launchpad FROM cryptorank_upcoming 
                    WHERE project_url = %s
                """, (url,))
                existing = cursor.fetchone()
                if existing:
                    existing_id = existing[0]
                    existing_investors = existing[2] if existing[2] else []
                    existing_launchpad = existing[3] if existing[3] else []
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
                else:
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
        conn = self.get_db_connection()
        if not conn:
            return
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            print("\n📊 Статистика базы данных:")
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
        print(f"\n✅ Готово!")
        print(f"📊 Обработано проектов: {result.get('total_projects', 0)}")
        print(f"🎯 Только проекты с конкретными датами (без TBA)")
    else:
        print("❌ Парсинг не удался")
    print("=" * 60)