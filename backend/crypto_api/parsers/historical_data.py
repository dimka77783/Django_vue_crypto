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

# Настройки БД (для чтения списка монет)
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
    # Указываем Selenium Manager использовать кеш в /app
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
        import psycopg2
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

def parse_historical_data(driver, symbol, base_url):
    """Парсинг исторических данных"""
    print(f"🔍 Парсим историю: {symbol}")
    print(f"🌐 URL: {base_url}")

    try:
        driver.set_page_load_timeout(30)
        driver.get(base_url)
        time.sleep(3)

        # === Ждём ТАБЛИЦУ — это ключевой признак существования данных ===
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            print("   ✅ Таблица найдена → страница существует")
        except:
            print(f"   ❌ Не найдено таблицы → возможно, монета не существует или данные не загружены")
            return []

        # === Теперь парсим таблицу ===
        table = driver.find_element(By.TAG_NAME, "table")
        rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # пропускаем заголовок
        if len(rows) == 0:
            print("   ⚠️ Таблица пустая")
            return []

        print(f"   📊 Найдено строк: {len(rows)}")

        parsed_data = []
        # Правильный порядок колонок
        headers = [
            "Date", "Open", "High", "Low", "Med", "Close",
            "Change", "Volume", "Change Volume", "Market Cap"
        ]

        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 6:  # минимум Date и Close
                    continue

                row_data = {}
                for i, header in enumerate(headers):
                    if i < len(cells):
                        cell_text = clean_value(cells[i].text)
                        row_data[header] = cell_text

                # Конвертируем дату
                raw_date = row_data.get("Date")
                date = convert_date_format(raw_date)
                if not date:
                    print(f"   ⚠️ Пропущена строка: некорректная дата '{raw_date}'")
                    continue

                row_data["Date"] = date
                parsed_data.append(row_data)

                # Логируем одну строку для проверки
                if len(parsed_data) == 1:
                    print(f"   ✅ Пример данных: {row_data}")

            except Exception as e:
                print(f"   ❌ Ошибка парсинга строки: {e}")
                continue

        print(f"✅ Добавлено записей: {len(parsed_data)}")
        return parsed_data

    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            print(f"   ⏳ Таймаут загрузки страницы")
        elif "404" in error_msg or "not found" in error_msg:
            print(f"   ❌ Страница не найдена (404)")
        else:
            print(f"   ❌ Неизвестная ошибка: {e}")
        return []

def save_to_json(data, filename=None):
    """Сохраняет данные в JSON файл"""
    if not data:
        print("❌ Нет данных для сохранения")
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = filename or f"historical_data_{timestamp}.json"

    result = {
        "scraped_at": datetime.now().isoformat(),
        "total_records": sum(len(d['data']) for d in data),
        "projects_count": len(data),
        "data": data
    }

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ Данные сохранены в: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Ошибка сохранения в JSON: {e}")
        return None

def main():
    """Главная функция — парсинг исторических данных для всех монет из БД"""
    driver = None
    all_data = []
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
            data = parse_historical_data(driver, symbol, url)

            if data:
                all_data.append({
                    "symbol": symbol,
                    "url": url,
                    "data": data
                })
            else:
                print(f"   ⚠️ Пропущена монета: {symbol} (нет данных или страница не найдена)")

            time.sleep(3)  # Антибан

        if all_data:
            save_to_json(all_data)
        else:
            print("❌ Ничего не найдено.")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        if driver:
            driver.quit()
        print("🔒 Браузер закрыт")

if __name__ == "__main__":
    main()