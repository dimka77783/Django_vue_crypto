#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import psycopg2

# Настройки БД
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', 'crypto_db'),
    'user': os.environ.get('DB_USER', 'crypto_user'),
    'password': os.environ.get('DB_PASSWORD', 'crypto_password')
}

def setup_driver():
    """Настройка браузера"""
    print("🔧 Запуск браузера...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-images')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    options.add_argument('--window-size=1920,1080')
    options.add_argument(f'--cache-dir={os.environ.get("WEBDRIVER_CACHE_DIR", "/app/.cache/selenium")}')
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    print("   ✅ Браузер готов")
    return driver

def convert_date_format(date_text):
    """Конвертирует дату из '11 Aug' или 'Aug 11' в 'YYYY-MM-DD'"""
    if not date_text or date_text == 'TBA':
        return None
    try:
        months = {
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        }
        parts = date_text.strip().split()
        if len(parts) < 2:
            return None
        day, month_text = None, None
        for p in parts:
            if p.isdigit():
                day = p.zfill(2)
            elif p[:3] in months:
                month_text = p[:3]
        if day and month_text:
            return f"2025-{months[month_text]}-{day}"
        return None
    except:
        return None

def clean_value(value):
    """Очищает значение от лишних символов"""
    if not value:
        return None
    value = value.strip()
    if value in ['-', '—', 'N/A', '', 'TBA']:
        return None
    return value

def get_coins_from_db():
    """Получает список монет из БД"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT project_symbol, project_url 
            FROM cryptorank_upcoming 
            WHERE project_symbol IS NOT NULL 
              AND project_url LIKE '%/ico/%'
            ORDER BY project_symbol
        """)
        rows = cursor.fetchall()
        conn.close()
        coins = []
        for symbol, url in rows:
            slug = url.split('/ico/')[-1].split('?')[0]
            hist_url = f"https://cryptorank.io/ru/price/{slug}/historical-data"
            coins.append((symbol, hist_url))
        print(f"📊 Найдено монет в БД: {len(coins)}")
        return coins
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return []

def create_table_if_not_exists(symbol):
    """Создаёт таблицу ohlc_<symbol>, если её нет"""
    conn = None
    cursor = None
    table_name = f"ohlc_{symbol.lower()}"
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                open_price NUMERIC(20,10),
                high_price NUMERIC(20,10),
                low_price NUMERIC(20,10),
                med_price NUMERIC(20,10),
                close_price NUMERIC(20,10),
                change_percent NUMERIC(10,6),
                volume_usd NUMERIC(30,10),
                change_volume_percent NUMERIC(10,6),
                market_cap NUMERIC(30,10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (date)
            );
        """)
        conn.commit()
        print(f"✅ Таблица {table_name} готова")
    except Exception as e:
        print(f"❌ Ошибка создания таблицы {table_name}: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def parse_historical_data(driver, symbol, base_url):
    """Парсинг исторических данных"""
    print(f"🔍 Парсим историю: {symbol}")
    print(f"🌐 URL: {base_url}")

    try:
        driver.set_page_load_timeout(30)
        driver.get(base_url)
        time.sleep(3)

        # Ждём таблицу
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            print("   ✅ Таблица найдена → страница существует")
        except:
            print(f"   ❌ Не найдено таблицы → возможно, монета не существует или данные не загружены")
            return []

        # Парсим таблицу
        table = driver.find_element(By.TAG_NAME, "table")
        rows = table.find_elements(By.TAG_NAME, "tr")[1:]
        if len(rows) == 0:
            print("   ⚠️ Таблица пустая")
            return []

        print(f"   📊 Найдено строк: {len(rows)}")

        parsed_data = []
        headers = [
            "Date", "Open", "High", "Low", "Med", "Close",
            "Change", "Volume", "Change Volume", "Market Cap"
        ]

        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 6:
                    continue

                row_data = {}
                for i, header in enumerate(headers):
                    if i < len(cells):
                        cell_text = clean_value(cells[i].text)
                        row_data[header] = cell_text

                raw_date = row_data.get("Date")
                date = convert_date_format(raw_date)
                if not date:
                    print(f"   ⚠️ Пропущена строка: некорректная дата '{raw_date}'")
                    continue

                # Преобразуем значения
                def extract_numeric(text):
                    if not text:
                        return None
                    try:
                        return float(text.replace('$', '').replace(',', '').replace('%', '').strip())
                    except:
                        return None

                open_price = extract_numeric(row_data.get("Open"))
                high_price = extract_numeric(row_data.get("High"))
                low_price = extract_numeric(row_data.get("Low"))
                med_price = extract_numeric(row_data.get("Med"))
                close_price = extract_numeric(row_data.get("Close"))
                change_percent = extract_numeric(row_data.get("Change"))
                volume_usd = extract_numeric(row_data.get("Volume"))
                change_volume_percent = extract_numeric(row_data.get("Change Volume"))
                market_cap = extract_numeric(row_data.get("Market Cap"))

                parsed_data.append({
                    'date': date,
                    'open_price': open_price,
                    'high_price': high_price,
                    'low_price': low_price,
                    'med_price': med_price,
                    'close_price': close_price,
                    'change_percent': change_percent,
                    'volume_usd': volume_usd,
                    'change_volume_percent': change_volume_percent,
                    'market_cap': market_cap
                })

                if len(parsed_data) == 1:
                    print(f"   ✅ Пример данных: {parsed_data[0]}")

            except Exception as e:
                print(f"   ❌ Ошибка парсинга строки: {e}")
                continue

        print(f"✅ Добавлено записей: {len(parsed_data)}")
        return parsed_data

    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            print(f"   ⏳ Таймаут загрузки страницы")
        elif "404" in error_msg:
            print(f"   ❌ Страница не найдена (404)")
        else:
            print(f"   ❌ Неизвестная ошибка: {e}")
        return []

def save_to_db(symbol, data):
    """Сохраняет данные в таблицу ohlc_<symbol>, не удаляя старые строки"""
    if not data:
        return

    table_name = f"ohlc_{symbol.lower()}"
    conn = None
    cursor = None

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Вставка данных (или обновление при конфликте по дате)
        insert_query = f"""
            INSERT INTO {table_name} (
                date, open_price, high_price, low_price, med_price,
                close_price, change_percent, volume_usd, change_volume_percent, market_cap
            ) VALUES (
                %(date)s, %(open_price)s, %(high_price)s, %(low_price)s, %(med_price)s,
                %(close_price)s, %(change_percent)s, %(volume_usd)s, %(change_volume_percent)s, %(market_cap)s
            )
            ON CONFLICT (date) DO UPDATE SET
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                med_price = EXCLUDED.med_price,
                close_price = EXCLUDED.close_price,
                change_percent = EXCLUDED.change_percent,
                volume_usd = EXCLUDED.volume_usd,
                change_volume_percent = EXCLUDED.change_volume_percent,
                market_cap = EXCLUDED.market_cap,
                created_at = CURRENT_TIMESTAMP;
        """

        for row in data:
            cursor.execute(insert_query, row)

        conn.commit()
        print(f"✅ Данные сохранены в {table_name}")

        # ❌ УДАЛЕНО: больше не удаляем старые строки

    except Exception as e:
        print(f"❌ Ошибка сохранения в БД: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def main():
    """Главная функция — парсинг исторических данных для всех монет из БД"""
    driver = None
    try:
        coins = get_coins_from_db()
        if not coins:
            print("❌ Нет монет для парсинга")
            return

        for i, (symbol, url) in enumerate(coins):
            # Перезапускаем драйвер каждые 10 монет
            if i % 10 == 0 and driver:
                driver.quit()
                time.sleep(2)
                driver = setup_driver()

            if not driver:
                driver = setup_driver()

            print(f"\n🔄 [{i+1}/{len(coins)}] Парсим: {symbol}")
            create_table_if_not_exists(symbol)
            data = parse_historical_data(driver, symbol, url)

            if data:
                save_to_db(symbol, data)
            else:
                print(f"   ⚠️ Пропущена монета: {symbol} (нет данных или страница не найдена)")

            time.sleep(3)  # Антибан

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        if driver:
            driver.quit()
        print("🔒 Браузер закрыт")

if __name__ == "__main__":
    main()