# Инструкция по развертыванию проекта

## Требования к системе

- Python 3.8 или выше
- PostgreSQL 9.6 или выше
- Git (опционально)

## Установка PostgreSQL

### Windows
1. Скачайте установщик с [официального сайта](https://www.postgresql.org/download/windows/)
2. Запустите установку, запомните пароль для пользователя postgres
3. Убедитесь, что сервис PostgreSQL запущен

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql