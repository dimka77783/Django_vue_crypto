#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import time
import os
import psycopg2
from psycopg2.extras import Json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from datetime import datetime

# 🔥 УСТАНАВЛИВАЕМ ПУТЬ ДЛЯ SELENIUM
os.environ['SELENIUM_CACHE_PATH'] = '/app/.cache/selenium'
os.makedirs('/app/.cache/selenium', exist_ok=True)

# Загрузка переменных из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Переменные из .env загружены")
except ImportError:
    print("⚠️ python-dotenv не установлен, используются системные переменные")

# Настройки БД из .env файла
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', 'crypto_db'),
    'user': os.environ.get('DB_USER', 'crypto_user'),
    'password': os.environ.get('DB_PASSWORD', 'crypto_password')
}

def update_project_investors_in_db(project_id, investors_list):
    """
    Обновляет столбец 'investors' в таблице 'cryptorank_upcoming' для заданного project_id.
    :param project_id: ID проекта в БД.
    :param investors_list: Список словарей с информацией об инвесторах.
    """
    connection = None
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        cursor = connection.cursor()
        if not investors_list:
            investors_data = Json([])
        else:
            investors_data = Json(investors_list)
        update_query = """
            UPDATE cryptorank_upcoming 
            SET investors = %s 
            WHERE id = %s;
        """
        cursor.execute(update_query, (investors_data, project_id))
        connection.commit()
        print(f"   ✅ Данные об инвесторах для project_id={project_id} успешно обновлены в БД.")
    except psycopg2.Error as db_err:
        print(f"   ❌ Ошибка БД при обновлении инвесторов: {db_err}")
        if connection:
            connection.rollback()
    except Exception as e:
        print(f"   ❌ Непредвиденная ошибка: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("   🔒 Соединение с БД закрыто.")

def setup_driver():
    """Настройка браузера"""
    print("🔧 Запуск браузера...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    print("   ✅ Браузер готов")
    return driver

def get_projects_from_db(limit=20):
    """Получаем проекты из БД"""
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        cursor = connection.cursor()
        query = """
        SELECT id, project_name, project_symbol, project_url 
        FROM cryptorank_upcoming 
        WHERE project_url IS NOT NULL 
        AND project_url != ''
        ORDER BY id 
        LIMIT %s
        """
        cursor.execute(query, (limit,))
        projects = cursor.fetchall()
        connection.close()
        print(f"📊 Получено проектов из БД: {len(projects)}")
        return [{'id': row[0], 'name': row[1], 'symbol': row[2], 'url': row[3].strip()} for row in projects if row[3].strip()]
    except Exception as e:
        print(f"⚠️ Ошибка БД: {e}")
        return []

def find_investors_table(driver):
    """Находит таблицу инвесторов"""
    try:
        header = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//h2[contains(text(), 'Investors and Backers') or contains(text(), 'Investors & Backers')]"
            ))
        )
        print(f"   📍 Заголовок 'Investors and Backers' найден: '{header.text.strip()}'")
        table = header.find_element(By.XPATH, "./following::table[1]")
        if table:
            print(f"   📊 Таблица инвесторов найдена.")
            return table
        return None
    except TimeoutException:
        print("   ⏳ Таймаут: Заголовок 'Investors and Backers' не найден.")
        return None
    except Exception as e:
        print(f"   ❌ Ошибка поиска таблицы: {e}")
        return None

def get_page_content_hash(table):
    """Генерирует хэш контента страницы"""
    try:
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        page_text_parts = []
        for row in rows:
            cells = row.find_elements(By.XPATH, "./td")
            name_text = cells[0].text.strip() if len(cells) > 0 else ""
            tier_text = cells[1].text.strip() if len(cells) > 1 else ""
            type_text = cells[2].text.strip() if len(cells) > 2 else ""
            stage_text = cells[3].text.strip() if len(cells) > 3 else ""
            row_text = f"{name_text}|{tier_text}|{type_text}|{stage_text}"
            if row_text and not (name_text.isdigit() and len(name_text) < 3 and not tier_text):
                page_text_parts.append(row_text)
        content = " || ".join(sorted(page_text_parts))
        return hash(content)
    except Exception as e:
        print(f"   ⚠️ Ошибка хэширования контента: {e}")
        return None

def collect_investors_from_table(table, project_info):
    """Собирает инвесторов из таблицы"""
    investors = []
    try:
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        print(f"   📊 Найдено строк в таблице: {len(rows)}")
        for i, row in enumerate(rows):
            try:
                cells = row.find_elements(By.XPATH, "./td")
                if len(cells) < 3:
                    continue
                # Извлечение данных
                full_text = cells[0].text.strip()
                parts = full_text.split('\n')
                investor_name = parts[0].strip()
                investor_role = parts[1].strip() if len(parts) > 1 else ""
                investor_tier = cells[1].text.strip() if len(cells) > 1 else ""
                investor_type = cells[2].text.strip() if len(cells) > 2 else ""
                investor_stage = cells[3].text.strip() if len(cells) > 3 else ""
                # Поиск ссылки
                investor_href = ""
                try:
                    link_element = cells[0].find_element(By.XPATH, ".//a[@href]")
                    href = link_element.get_attribute('href')
                    if href and ('/funds/' in href or '/investors/' in href or '/companies/' in href):
                        investor_href = href
                except:
                    pass
                investor = {
                    'project_id': project_info['id'],
                    'project_name': project_info['name'],
                    'project_url': project_info['url'],
                    'investor_name': investor_name,
                    'investor_role': investor_role,
                    'investor_tier': investor_tier,
                    'investor_type': investor_type,
                    'investor_stage': investor_stage,
                    'investor_href': investor_href
                }
                investors.append(investor)
            except Exception as e:
                print(f"   ⚠️ Ошибка обработки строки {i + 1}: {e}")
                continue
    except Exception as e:
        print(f"   ❌ Ошибка сбора инвесторов: {e}")
    print(f"   ✅ Собрано {len(investors)} инвесторов со страницы.")
    return investors

def find_next_page_button(table):
    """Ищет кнопку 'Next'"""
    try:
        # Поиск контейнера пагинации
        pagination_container = None
        try:
            elements_after_table = table.find_elements(By.XPATH, "./following::*")
            for elem in elements_after_table:
                elem_classes = (elem.get_attribute('class') or '').lower()
                if 'pagination' in elem_classes or 'sc-' in elem_classes or \
                        elem.find_elements(By.XPATH, ".//button[@aria-label='Next page']"):
                    pagination_container = elem
                    break
                if len(elements_after_table) > 20:
                    break
        except Exception as e:
            print(f"   ⚠️ Ошибка поиска пагинации: {e}")

        if not pagination_container:
            try:
                pagination_container = table.find_element(By.XPATH, "./following-sibling::*[1]")
            except:
                pass

        if not pagination_container:
            try:
                parent = table.find_element(By.XPATH, "..")
                pagination_containers = parent.find_elements(By.XPATH,
                                                             "./*[contains(@class, 'pagination') or contains(@class, 'styles_pagination')]")
                if pagination_containers:
                    pagination_container = pagination_containers[0]
            except Exception as e_inner:
                print(f"   ⚠️ Ошибка поиска пагинации: {e_inner}")

        if not pagination_container:
            print("   ⚠️ Контейнер пагинации не найден.")
            return None

        # Поиск кнопки "Next"
        try:
            next_button = pagination_container.find_element(By.XPATH,
                                                            ".//button[@aria-label='Next page' and not(@disabled)]")
            if next_button.is_displayed() and next_button.is_enabled():
                print(f"   🎯 Найдена кнопка Next по aria-label")
                return next_button
        except:
            pass

        try:
            svg_next_buttons = pagination_container.find_elements(By.XPATH,
                                                                  ".//button[not(@disabled)]//svg//path[contains(@d, 'M6.994 5.002')]")
            for svg_path in svg_next_buttons:
                try:
                    button = svg_path.find_element(By.XPATH, "./ancestor::button[1]")
                    if button.is_displayed() and button.is_enabled() and not button.get_attribute('disabled'):
                        print(f"   🎯 Найдена кнопка Next по SVG")
                        return button
                except:
                    continue
        except Exception as e_svg:
            print(f"   ⚠️ Ошибка поиска кнопки Next по SVG: {e_svg}")

        try:
            page_buttons = pagination_container.find_elements(By.XPATH,
                                                              ".//button[contains(@class, 'styles_button__')]")
            current_page = None
            max_page = 0
            page_elements = {}
            for button in page_buttons:
                try:
                    if not button.is_displayed() or not button.is_enabled() or button.get_attribute('disabled'):
                        continue
                    span = button.find_element(By.XPATH, ".//span[contains(@class, 'styles_text__')]")
                    text = span.text.strip()
                    if text.isdigit():
                        page_num = int(text)
                        page_elements[page_num] = button
                        max_page = max(max_page, page_num)
                        classes = button.get_attribute('class') or ''
                        if 'styles_selected__' in classes:
                            current_page = page_num
                except Exception as e_btn:
                    continue

            if current_page is not None:
                if current_page < max_page:
                    next_page = current_page + 1
                    if next_page in page_elements:
                        print(f"   ➡️ Переход на страницу {next_page}")
                        return page_elements[next_page]
                else:
                    print(f"   ⏹️ Достигнута последняя страница ({current_page}).")
                    return None
            else:
                if 2 in page_elements:
                    page_1_button = page_elements.get(1)
                    if page_1_button:
                        classes_1 = page_1_button.get_attribute('class') or ''
                        if 'styles_selected__' in classes_1:
                            print(f"   ➡️ Переход на страницу 2")
                            return page_elements[2]
        except Exception as e_num:
            print(f"   ⚠️ Ошибка поиска числовой пагинации: {e_num}")

    except Exception as e:
        print(f"   ⚠️ Ошибка поиска контейнера пагинации: {e}")
    print("   ⏹️ Кнопка 'Next' не найдена.")
    return None

def process_investors_with_pagination(driver, project_info):
    """Обрабатывает пагинацию"""
    all_investors = []
    current_page = 1
    max_pages = 15
    seen_hashes = set()
    table = find_investors_table(driver)
    if not table:
        print("   ❌ Не удалось найти таблицу с инвесторами.")
        return all_investors

    while current_page <= max_pages:
        print(f"\n   📄 Обработка страницы {current_page}...")
        page_hash = get_page_content_hash(table)
        if page_hash is not None:
            if page_hash in seen_hashes:
                print(f"   ⚠️ Контент страницы {current_page} уже был. Остановка.")
                break
            else:
                seen_hashes.add(page_hash)
        else:
            print(f"   ⚠️ Не удалось получить хэш для страницы {current_page}")

        investors = collect_investors_from_table(table, project_info)
        if not investors and current_page > 1:
            print(f"   ⚠️ Страница {current_page} пуста. Конец.")
            break
        all_investors.extend(investors)
        print(f"   📈 Всего инвесторов на данный момент: {len(all_investors)}")

        if current_page == 1:
            next_button = find_next_page_button(table)
            if not next_button:
                print(f"   📄 Пагинация не обнаружена.")
                break

        next_button = find_next_page_button(table)
        if not next_button or not next_button.is_displayed() or not next_button.is_enabled():
            print(f"   ⏹️ Кнопка 'Next' не найдена или недоступна. Завершение.")
            break

        print(f"   🔽 Прокрутка к кнопке 'Next'...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
        time.sleep(1.5)

        print(f"   🖱️ Клик по кнопке 'Next'...")
        try:
            driver.execute_script("arguments[0].click();", next_button)
        except Exception as e:
            print(f"   ❌ Ошибка клика: {e}")
            break

        print(f"   ⏳ Ожидание загрузки новой страницы...")
        time.sleep(2.5)

        try:
            WebDriverWait(driver, 15).until(EC.staleness_of(table))
            print(f"   ✅ Старая таблица устарела.")
        except TimeoutException:
            print(f"   ⚠️ Старая таблица не устарела.")
            new_table = find_investors_table(driver)
            if new_table:
                new_hash = get_page_content_hash(new_table)
                if new_hash == page_hash:
                    print(f"   ⚠️ Контент не изменился. Завершение.")
                    break
                else:
                    table = new_table
            else:
                print(f"   ❌ Новая таблица не найдена. Завершение.")
                break

        print(f"   🔍 Поиск новой таблицы...")
        new_table = find_investors_table(driver)
        if not new_table:
            print(f"   ❌ Новая таблица не найдена. Завершение.")
            break
        table = new_table
        current_page += 1
        print("-" * 40)
    return all_investors

def scan_project_investors(driver, project_info):
    """Сканирует инвесторов для одного проекта"""
    try:
        print(f"\n🔍 СБОР ИНВЕСТОРОВ: {project_info['name']} ({project_info['symbol']})")
        print(f"🌐 URL: {project_info['url']}")
        driver.set_page_load_timeout(90)
        driver.get(project_info['url'])
        print("   ⏳ Страница загружена. Ожидание...")
        time.sleep(6)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        investors = process_investors_with_pagination(driver, project_info)
        print(f"\n   ✅ Завершено. Найдено инвесторов: {len(investors)}")
        if investors:
            print(f"   📋 Примеры (первые 5):")
            for inv in investors[:5]:
                role_str = f" ({inv['investor_role']})" if inv['investor_role'] else ""
                tier_str = f", Tier: {inv['investor_tier']}"
                type_str = f", Type: {inv['investor_type']}"
                stage_str = f", Stage: {inv['investor_stage']}" if inv['investor_stage'] else ""
                print(f"      👥 {inv['investor_name']}{role_str}{tier_str}{type_str}{stage_str}")
            if len(investors) > 5:
                print(f"      ... и еще {len(investors) - 5} инвесторов.")
        else:
            print("   ℹ️ Инвесторы не найдены.")
        return investors
    except Exception as e:
        print(f"   ❌ Ошибка сканирования проекта {project_info['name']}: {e}")
        import traceback
        traceback.print_exc()
        return []

def remove_duplicates(investors):
    """Удаляет дубликаты инвесторов"""
    print(f"\n🔧 Удаление дубликатов...")
    print(f"📊 До: {len(investors)} записей")
    seen = set()
    unique = []
    for inv in investors:
        key = (
            inv['project_id'],
            inv['investor_name'].lower().strip(),
            inv.get('investor_href', '').strip()
        )
        if key not in seen:
            seen.add(key)
            unique.append(inv)
    print(f"✅ После: {len(unique)} уникальных записей")
    return unique

def save_to_json(investors):
    """Сохраняет результаты в JSON файл"""
    if not investors:
        print("\nℹ️ Нет данных для сохранения.")
        return None
    try:
        unique_investors = remove_duplicates(investors)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        data = {
            "scan_info": {
                "timestamp": datetime.now().isoformat(),
                "total_found": len(investors),
                "unique_investors": len(unique_investors),
                "duplicates_removed": len(investors) - len(unique_investors),
                "projects_scanned": len(set(inv['project_name'] for inv in unique_investors))
            },
            "investors": unique_investors
        }
        filename = f"investors_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Данные успешно сохранены в файл: {filename}")
        print(f"   📊 Уникальных инвесторов: {len(unique_investors)}")
        return filename
    except Exception as e:
        print(f"❌ Ошибка сохранения в JSON: {e}")
        return None

def analyze_results(investors):
    """Анализирует собранные данные"""
    if not investors:
        print("\n❌ Нет данных для анализа.")
        return
    unique_investors = remove_duplicates(investors)
    print(f"\n📈 АНАЛИЗ СОБРАННЫХ ДАННЫХ")
    print("=" * 50)
    projects_data = {}
    investor_names = {}
    investor_types = {}
    investor_tiers = {}
    for inv in unique_investors:
        pname = inv['project_name']
        iname = inv['investor_name']
        itype = inv['investor_type']
        itier = inv['investor_tier']
        if pname not in projects_data:
            projects_data[pname] = {'count': 0, 'investors': []}
        projects_data[pname]['count'] += 1
        projects_data[pname]['investors'].append(inv)
        investor_names[iname] = investor_names.get(iname, 0) + 1
        if itype:
            investor_types[itype] = investor_types.get(itype, 0) + 1
        if itier:
            investor_tiers[itier] = investor_tiers.get(itier, 0) + 1

    print(f"🎯 Всего проектов: {len(projects_data)}")
    print(f"👥 Уникальных инвесторов: {len(investor_names)}")
    print(f"🏷️  Уникальных типов: {len(investor_types)}")
    print(f"🏅 Уникальных уровней (Tier): {len(investor_tiers)}")

    print(f"\n🏅 ТОП-10 самых активных инвесторов:")
    top_investors = sorted(investor_names.items(), key=lambda item: item[1], reverse=True)[:10]
    for i, (name, count) in enumerate(top_investors, 1):
        print(f"   {i:2d}. {name:<30} ({count} проектов)")

    if investor_types:
        print(f"\n🏷️  Распределение по типам:")
        sorted_types = sorted(investor_types.items(), key=lambda item: item[1], reverse=True)
        for type_name, count in sorted_types:
            print(f"   - {type_name:<20} ({count})")

    if investor_tiers:
        print(f"\n🎖️  Распределение по уровням (Tier):")
        sorted_tiers = sorted(investor_tiers.items(),
                              key=lambda item: (item[0].isdigit(), int(item[0]) if item[0].isdigit() else item[0]))
        for tier, count in sorted_tiers:
            print(f"   - Tier {tier:<18} ({count})")

    print(f"\n🗂️  ДЕТАЛИЗАЦИЯ ПО ПРОЕКТАМ:")
    for pname, pdata in projects_data.items():
        print(f"\n   🎯 {pname} ({pdata['count']} инвесторов):")
        for inv in pdata['investors'][:3]:
            role_str = f" ({inv['investor_role']})" if inv['investor_role'] else ""
            tier_str = f", Tier: {inv['investor_tier']}"
            type_str = f", Type: {inv['investor_type']}"
            stage_str = f", Stage: {inv['investor_stage']}" if inv['investor_stage'] else ""
            print(f"      👥 {inv['investor_name']}{role_str}{tier_str}{type_str}{stage_str}")
        if len(pdata['investors']) > 3:
            print(f"      ... и еще {len(pdata['investors']) - 3} инвесторов.")

def main():
    """Главная функция"""
    driver = None
    all_investors = []
    try:
        print("🚀 СТАРТ ПАРСИНГА ИНВЕСТОРОВ CRYPTORANK")
        print("=" * 50)
        projects = get_projects_from_db(20)
        if not projects:
            print("❌ Не удалось получить список проектов.")
            return
        print(f"📋 Количество проектов для обработки: {len(projects)}")
        driver = setup_driver()
        for i, project in enumerate(projects, 1):
            print(f"\n{'=' * 20} ПРОЕКТ {i}/{len(projects)} {'=' * 20}")
            project_investors = scan_project_investors(driver, project)
            if project_investors is not None:
                update_project_investors_in_db(project['id'], project_investors)
            all_investors.extend(project_investors)
            if i < len(projects):
                print(f"\n⏳ Пауза 3 секунды...")
                time.sleep(3)
        if all_investors:
            print(f"\n{'=' * 20} ИТОГИ {'=' * 20}")
            analyze_results(all_investors)
            save_to_json(all_investors)
        else:
            print("\n😔 Не удалось собрать данные.")
    except KeyboardInterrupt:
        print("\n⚠️ Прервано пользователем.")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver is not None:
            try:
                driver.quit()
            except:
                pass
        # 🔥 Принудительное завершение процессов
        os.system("killall -q chrome chromedriver 2>/dev/null || true")
        print("\n🔒 Браузер закрыт (принудительно)")