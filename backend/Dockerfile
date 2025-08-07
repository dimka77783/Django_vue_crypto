FROM python:3.11-slim

# Устанавливаем зависимости для Chrome
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libc6 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    libgbm1 \
    libgtk-3-0 \
    libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

# Добавляем репозиторий Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome-keyring.gpg
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Устанавливаем Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable && rm -rf /var/lib/apt/lists/*

# Устанавливаем Python-зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Настройка кеша Selenium
ENV SELENIUM_CACHE_PATH=/tmp/selenium
RUN mkdir -p /tmp/selenium && chmod -R 777 /tmp/selenium

# Рабочая директория
WORKDIR /app
COPY . .

# Права пользователя
#USER 1000:1000

# Запуск
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]