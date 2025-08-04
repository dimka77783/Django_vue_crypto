#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import time
import os
import psycopg2
from psycopg2.extras import Json  # Импортируем Json адаптер
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from datetime import datetime

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


# --- НОВАЯ ФУНКЦИЯ ДЛЯ СОХРАНЕНИЯ В БД ---
def update_project_investors_in_db(project_id, investors_list):
    """
    Обновляет столбец 'investors' в таблице 'cryptorank_upcoming' для заданного project_id.

    :param project_id: ID проекта в БД.
    :param investors_list: Список словарей с информацией об инвесторах.
    """
    connection = None
    try:
        # Подключение к БД
        connection = psycopg2.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Подготовка данных для вставки
        # psycopg2.extras.Json автоматически сериализует объект Python в JSON для PostgreSQL
        if not investors_list:
            investors_data = Json([])  # Записываем пустой массив, если нет инвесторов
        else:
            # Можно оставить оригинальные ключи из парсера
            investors_data = Json(investors_list)

        # SQL-запрос для обновления
        update_query = """
            UPDATE cryptorank_upcoming 
            SET investors = %s 
            WHERE id = %s;
        """

        # Выполнение запроса
        cursor.execute(update_query, (investors_data, project_id))

        # Фиксация изменений
        connection.commit()

        print(f"   ✅ Данные об инвесторах для project_id={project_id} успешно обновлены в БД.")

    except psycopg2.Error as db_err:
        print(f"   ❌ Ошибка БД при обновлении инвесторов для project_id={project_id}: {db_err}")
        if connection:
            connection.rollback()  # Откат транзакции в случае ошибки
    except Exception as e:
        print(f"   ❌ Непредвиденная ошибка при обновлении инвесторов для project_id={project_id}: {e}")
        if connection:
            connection.rollback()
    finally:
        # Закрытие соединения
        if connection:
            cursor.close()
            connection.close()
            print("   🔒 Соединение с БД закрыто.")


# --- КОНЕЦ НОВОЙ ФУНКЦИИ ---

def setup_driver():
    """Настройка браузера"""
    print("🔧 Запуск браузера...")
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless=new') # Закомментируйте для отладки
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)  # Уменьшено
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
        return [{'id': row[0], 'name': row[1], 'symbol': row[2], 'url': row[3].strip()} for row in projects if
                row[3].strip()]
    except Exception as e:
        print(f"⚠️ Ошибка БД, используем тестовые данные: {e}")
        # Тестовые данные для проверки
        return [
            {
                'id': 10,
                'name': 'TheoriqAI',
                'symbol': 'THQ',
                'url': 'https://cryptorank.io/ico/theoriqai'
            },
            {
                'id': 1,
                'name': 'OneFootball',
                'symbol': 'OFC',
                'url': 'https://cryptorank.io/ico/onefootballcom'
            }
            # Добавьте сюда другие проекты для теста
        ]


def find_investors_table(driver):
    """
    Находит таблицу инвесторов.
    Опирается на заголовок 'Investors and Backers' и следующую за ним таблицу.
    """
    try:
        # Найти заголовок
        header = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//h2[contains(text(), 'Investors and Backers') or contains(text(), 'Investors & Backers')]"
            ))
        )
        print(f"   📍 Заголовок 'Investors and Backers' найден: '{header.text.strip()}'")
        # Найти таблицу сразу после заголовка
        table = header.find_element(By.XPATH, "./following::table[1]")
        if table:
            print(f"   📊 Таблица инвесторов найдена.")
            return table
        else:
            print("   ❌ Таблица инвесторов не найдена после заголовка.")
            return None
    except TimeoutException:
        print("   ⏳ Таймаут: Заголовок 'Investors and Backers' не найден.")
        return None
    except Exception as e:
        print(f"   ❌ Ошибка поиска таблицы инвесторов: {e}")
        return None


def get_page_content_hash(table):
    """Генерирует хэш контента страницы по тексту строк таблицы для проверки уникальности."""
    try:
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        page_text_parts = []
        for row in rows:
            cells = row.find_elements(By.XPATH, "./td")
            # Собираем текст из ключевых ячеек для хэширования
            # Name (0), Tier (1), Type (2), Stage (3)
            name_text = cells[0].text.strip() if len(cells) > 0 else ""
            tier_text = cells[1].text.strip() if len(cells) > 1 else ""
            type_text = cells[2].text.strip() if len(cells) > 2 else ""
            stage_text = cells[3].text.strip() if len(cells) > 3 else ""
            row_text = f"{name_text}|{tier_text}|{type_text}|{stage_text}"
            # Исключаем строки, которые явно не про инвесторов (например, пагинация)
            if row_text and not (name_text.isdigit() and len(name_text) < 3 and not tier_text):
                page_text_parts.append(row_text)
        content = " || ".join(sorted(page_text_parts))  # Сортируем для стабильности
        # print(f"DEBUG: Hashing content: {content}") # Для отладки
        return hash(content)
    except Exception as e:
        print(f"   ⚠️ Ошибка хэширования контента страницы: {e}")
        return None


def collect_investors_from_table(table, project_info):
    """Собирает инвесторов из таблицы."""
    investors = []
    try:
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        print(f"   📊 Найдено строк в таблице: {len(rows)}")
        for i, row in enumerate(rows):
            try:
                cells = row.find_elements(By.XPATH, "./td")
                # Проверка на минимальное количество ячеек (Name, Tier, Type)
                if len(cells) < 3:
                    print(f"   ⚠️ Строка {i + 1} имеет недостаточно ячеек ({len(cells)}), пропущена.")
                    continue
                # --- Извлечение данных по ячейкам ---
                # Name (первая ячейка, индекс 0)
                name_cell = cells[0]
                full_text = name_cell.text.strip()
                # Валидация имени: не пустое, не просто число, не прочерк
                if not full_text or (full_text.isdigit() and len(full_text) < 3) or full_text in ["-", ""]:
                    print(f"   ⚠️ Недопустимое имя инвестора в строке {i + 1}: '{full_text}', пропущено.")
                    continue
                # Разделение имени и роли (если есть, например, "Lead" на новой строке)
                parts = full_text.split('\n')  # Исправлено: \n вместо '
                investor_name = parts[0].strip()
                investor_role = parts[1].strip() if len(parts) > 1 else ""
                # Tier (вторая ячейка, индекс 1)
                investor_tier = cells[1].text.strip() if len(cells) > 1 else ""
                # Type (третья ячейка, индекс 2)
                investor_type = cells[2].text.strip() if len(cells) > 2 else ""
                # Stage (четвертая ячейка, индекс 3, если существует)
                investor_stage = cells[3].text.strip() if len(cells) > 3 else ""
                # Href (ссылка внутри ячейки имени)
                investor_href = ""
                try:
                    # Ищем ссылку внутри ячейки с именем
                    link_element = name_cell.find_element(By.XPATH, ".//a[@href]")
                    href = link_element.get_attribute('href')
                    # Проверка, что ссылка ведет на фонд/инвестора
                    if href and ('/funds/' in href or '/investors/' in href or '/companies/' in href):
                        investor_href = href

                except:
                    pass  # Ссылка не обязательна
                # -----------------------------
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
                # print(f"      👥 {investor_name} ({investor_role}) - Tier: {investor_tier}, Type: {investor_type}") # Для отладки
            except Exception as e:
                print(f"   ⚠️ Ошибка обработки строки {i + 1}: {e}")
                # import traceback
                # traceback.print_exc() # Раскомментируйте для подробной отладки
                continue

    except Exception as e:
        print(f"   ❌ Ошибка сбора инвесторов из таблицы: {e}")
        # import traceback
        # traceback.print_exc() # Раскомментируйте для подробной отладки

    print(f"   ✅ Собрано {len(investors)} инвесторов со страницы.")
    return investors


def find_next_page_button(table):
    """
    Ищет кнопку "Next" или следующую страницу.
    Учитывает специфичную структуру пагинации CryptoRank.
    """
    try:
        # --- Улучшенный и правильный поиск контейнера пагинации ---
        pagination_container = None
        # 1. Попробуем найти пагинацию как элемент, следующий ПОСЛЕ таблицы
        try:
            elements_after_table = table.find_elements(By.XPATH, "./following::*")
            for elem in elements_after_table:
                elem_classes = (elem.get_attribute('class') or '').lower()
                if 'pagination' in elem_classes or 'sc-' in elem_classes or \
                        elem.find_elements(By.XPATH, ".//button[@aria-label='Next page']") or \
                        elem.find_elements(By.XPATH, ".//button[contains(@class, 'styles_button__')]"):
                    pagination_container = elem
                    print(
                        f"   📦 Найден контейнер пагинации после таблицы (tag: {elem.tag_name}, class: {elem.get_attribute('class')}).")
                    break
                # Ограничение поиска
                if len(elements_after_table) > 20:
                    break
        except Exception as e:
            print(f"   ⚠️ Ошибка поиска пагинации через following::*: {e}")
        if not pagination_container:
            try:
                pagination_container = table.find_element(By.XPATH, "./following-sibling::*[1]")
                print(f"   📦 Найден контейнер пагинации как следующий sibling (tag: {pagination_container.tag_name}).")
            except:
                pass
        if not pagination_container:
            try:
                parent = table.find_element(By.XPATH, "..")
                pagination_containers = parent.find_elements(By.XPATH,
                                                             "./*[contains(@class, 'pagination') or contains(@class, 'styles_pagination') or contains(@class, 'sc-')]")
                if pagination_containers:
                    pagination_container = pagination_containers[0]
                    print(f"   📦 Найден контейнер пагинации внутри родителя (tag: {pagination_container.tag_name}).")
            except Exception as e_inner:
                print(f"   ⚠️ Ошибка поиска пагинации внутри родителя: {e_inner}")
        if not pagination_container:
            print("   ⚠️ Контейнер пагинации не найден рядом с таблицей.")
            return None
        # --- Поиск самой кнопки "Next" внутри найденного контейнера ---
        # 1. Ищем кнопку "Next page" по aria-label (САМЫЙ НАДЕЖНЫЙ СПОСОБ)
        try:
            next_button = pagination_container.find_element(By.XPATH,
                                                            ".//button[@aria-label='Next page' and not(@disabled)]")
            if next_button.is_displayed() and next_button.is_enabled():
                print(f"   🎯 Найдена кнопка Next по aria-label")
                return next_button
        except:
            pass
        # 2. Ищем кнопку с SVG стрелкой вправо
        try:
            svg_next_buttons = pagination_container.find_elements(By.XPATH,
                                                                  ".//button[not(@disabled)]//svg//path[contains(@d, 'M6.994 5.002') or contains(@d, 'm8.002') or contains(@d, 'M8.002')]")
            for svg_path in svg_next_buttons:
                try:
                    button = svg_path.find_element(By.XPATH, "./ancestor::button[1]")
                    if button.is_displayed() and button.is_enabled() and not button.get_attribute('disabled'):
                        print(f"   🎯 Найдена кнопка Next по SVG (стрелка вправо)")
                        return button
                except:
                    continue
        except Exception as e_svg:
            print(f"   ⚠️ Ошибка поиска кнопки Next по SVG: {e_svg}")
        # 3. Ищем числовую пагинацию и определяем следующую страницу
        try:
            page_buttons = pagination_container.find_elements(By.XPATH,
                                                              ".//button[contains(@class, 'styles_button__') and .//span[contains(@class, 'styles_text__') and text()[normalize-space(.) != '']]]")
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
                            print(f"   📍 Текущая страница: {page_num}")
                except Exception as e_btn:
                    continue
            # --- ИСПРАВЛЕННАЯ ЛОГИКА ---
            # Если нашли текущую страницу
            if current_page is not None:
                # И если текущая страница НЕ является последней
                if current_page < max_page:
                    next_page = current_page + 1
                    if next_page in page_elements:
                        print(f"   ➡️ Переход на страницу {next_page} (по числовой пагинации)")
                        return page_elements[next_page]
                else:
                    # Если current_page == max_page, значит, мы на последней странице
                    print(f"   ⏹️ Достигнута последняя страница ({current_page}).")
                    return None  # Возвращаем None, чтобы остановить пагинацию
            else:
                # Если не смогли определить текущую страницу (например, на первой странице)
                # И если страница 2 существует, переходим на нее
                # Это логика "по умолчанию" только для начального перехода
                if page_elements and 2 in page_elements:
                    # Проверим, является ли 1 текущей (выбранной)
                    page_1_button = page_elements.get(1)
                    if page_1_button:
                        classes_1 = page_1_button.get_attribute('class') or ''
                        if 'styles_selected__' in classes_1:
                            print(f"   ➡️ Переход на страницу 2 (по умолчанию с первой страницы)")
                            return page_elements[2]
                    # Если 1 не выбрана, возможно, мы на другой странице или логика другая.
                    # В этом случае безопаснее не делать переход по умолчанию.
                    print(f"   ⚠️ Текущая страница не определена, но страница 2 найдена. Ожидаем явной кнопки 'Next'.")
            # Если ни одна из вышеуказанных проверок не сработала
            print(f"   ⏹️ Кнопка 'Next' по числовой пагинации не найдена.")
        except Exception as e_num:
            print(f"   ⚠️ Ошибка поиска числовой пагинации: {e_num}")
    except Exception as e:
        print(f"   ⚠️ Ошибка поиска контейнера пагинации: {e}")

    print("   ⏹️ Кнопка 'Next' или следующая страница не найдены.")
    return None  # Явно возвращаем None в конце


def process_investors_with_pagination(driver, project_info):
    """Обрабатывает пагинацию и собирает всех инвесторов."""
    all_investors = []
    current_page = 1
    max_pages = 15  # Увеличено для проектов с большим количеством инвесторов
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
                print(f"   ⚠️ Контент страницы {current_page} уже был (хэш совпадает). Остановка.")
                break
            else:
                seen_hashes.add(page_hash)
        else:
            print(f"   ⚠️ Не удалось получить хэш для страницы {current_page}")
        investors = collect_investors_from_table(table, project_info)
        # Защита от зацикливания: если на странице нет валидных инвесторов (кроме первой)
        if not investors and current_page > 1:
            print(f"   ⚠️ Страница {current_page} пуста. Конец.")
            break
        all_investors.extend(investors)
        print(f"   📈 Всего инвесторов на данный момент: {len(all_investors)}")
        # Если это первая страница, проверим наличие пагинации
        if current_page == 1:
            next_button = find_next_page_button(table)
            if not next_button:
                print(f"   📄 Пагинация не обнаружена или закончилась.")
                break
            else:
                print(f"   🔄 Обнаружена пагинация.")
        # Находим кнопку "Next"
        next_button = find_next_page_button(table)
        if not next_button:
            print(f"   ⏹️ Кнопка 'Next' не найдена. Завершение.")
            break
        if not next_button.is_displayed() or not next_button.is_enabled():
            print(f"   ⏹️ Кнопка 'Next' недоступна. Завершение.")
            break
        print(f"   🔽 Прокрутка к кнопке 'Next'...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
        time.sleep(1.5)  # Увеличено немного
        print(f"   🖱️ Клик по кнопке 'Next'...")
        try:
            driver.execute_script("arguments[0].click();", next_button)
        except Exception as e:
            print(f"   ❌ Ошибка клика: {e}")
            break
        print(f"   ⏳ Ожидание загрузки новой страницы...")
        time.sleep(2.5)  # Увеличено немного
        # Надежное ожидание обновления таблицы
        try:
            # Ждем, пока старая таблица станет stale
            WebDriverWait(driver, 15).until(EC.staleness_of(table))
            print(f"   ✅ Старая таблица устарела.")
        except TimeoutException:
            print(f"   ⚠️ Старая таблица не устарела. Проверка содержимого...")
            # Если не устарела, проверим хэш
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
        except Exception as e:
            print(f"   ⚠️ Ошибка ожидания обновления: {e}")
            # Просто продолжаем и ищем новую таблицу
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
    """Сканирует инвесторов для одного проекта."""
    try:
        print(f"\n🔍 СБОР ИНВЕСТОРОВ: {project_info['name']} ({project_info['symbol']})")
        print(f"🌐 URL: {project_info['url']}")
        driver.set_page_load_timeout(90)  # Увеличено
        driver.get(project_info['url'])
        print("   ⏳ Страница загружена. Ожидание...")
        time.sleep(6)  # Увеличено
        # Небольшая прокрутка для подгрузки контента
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        investors = process_investors_with_pagination(driver, project_info)
        print(f"\n   ✅ Завершено. Найдено инвесторов: {len(investors)}")
        if investors:
            print(f"   📋 Примеры (первые 5):")
            for inv in investors[:5]:  # Показываем только первые 5 для краткости
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
    """Удаляет дубликаты инвесторов."""
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
    """Сохраняет результаты в JSON файл."""
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
    """Анализирует собранные данные."""
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
        # Сортируем по числовому значению, если возможно
        sorted_tiers = sorted(investor_tiers.items(),
                              key=lambda item: (item[0].isdigit(), int(item[0]) if item[0].isdigit() else item[0]))
        for tier, count in sorted_tiers:
            print(f"   - Tier {tier:<18} ({count})")
    print(f"\n🗂️  ДЕТАЛИЗАЦИЯ ПО ПРОЕКТАМ:")
    for pname, pdata in projects_data.items():
        print(f"\n   🎯 {pname} ({pdata['count']} инвесторов):")
        for inv in pdata['investors'][:3]:  # Показываем первых 3 инвесторов
            role_str = f" ({inv['investor_role']})" if inv['investor_role'] else ""
            tier_str = f", Tier: {inv['investor_tier']}"
            type_str = f", Type: {inv['investor_type']}"
            stage_str = f", Stage: {inv['investor_stage']}" if inv['investor_stage'] else ""
            print(f"      👥 {inv['investor_name']}{role_str}{tier_str}{type_str}{stage_str}")
        if len(pdata['investors']) > 3:
            print(f"      ... и еще {len(pdata['investors']) - 3} инвесторов.")


def main():
    """Главная функция."""
    driver = setup_driver()
    all_investors = []
    try:
        print("🚀 СТАРТ ПАРСИНГА ИНВЕСТОРОВ CRYPTORANK")
        print("=" * 50)
        projects = get_projects_from_db(20)
        if not projects:
            print("❌ Не удалось получить список проектов.")
            return
        print(f"📋 Количество проектов для обработки: {len(projects)}")
        for i, project in enumerate(projects, 1):
            print(f"\n{'=' * 20} ПРОЕКТ {i}/{len(projects)} {'=' * 20}")
            project_investors = scan_project_investors(driver, project)
            # --- НОВАЯ СТРОЧКА: Сохранение в БД сразу после сбора для проекта ---
            if project_investors is not None:  # Убедиться, что функция возвращает список (пустой или нет)
                update_project_investors_in_db(project['id'], project_investors)
            # ------------------------------------------------------------------
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
        driver.quit()
        print("\n🔒 Браузер закрыт.")
