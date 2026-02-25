"""
Модуль для работы с конфигурацией и скрытыми данными.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import json
from dotenv import load_dotenv


class Config:
    """Класс для управления конфигурацией приложения."""

    def __init__(self, env_file: Optional[str] = None):
        """
        Инициализация конфигурации.

        Args:
            env_file (Optional[str]): Путь к .env файлу
        """
        # Загружаем переменные окружения
        if env_file:
            load_dotenv(env_file)
        else:
            # Ищем .env файл в корне проекта
            env_path = Path(__file__).parent.parent.parent / '.env'
            if env_path.exists():
                load_dotenv(env_path)
            else:
                # Если .env нет, пробуем загрузить из .env.example
                example_path = Path(__file__).parent.parent.parent / '.env.example'
                if example_path.exists():
                    load_dotenv(example_path)
                    print("⚠️  Используется .env.example. Создайте .env файл с вашими настройками!")

        # Параметры подключения к БД
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'hh_parser'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres'),
            'port': os.getenv('DB_PORT', '5432')
        }

        # Параметры API
        self.api_config = {
            'base_url': os.getenv('HH_API_BASE_URL', 'https://api.hh.ru/'),
            'timeout': int(os.getenv('HH_API_TIMEOUT', '30')),
            'max_retries': int(os.getenv('HH_API_MAX_RETRIES', '3'))
        }

        self.companies_file = Path(__file__).parent.parent.parent / 'data' / 'companies.json'

    def get_db_connection_params(self) -> Dict[str, str]:
        """
        Получение параметров подключения к БД.

        Returns:
            Dict[str, str]: Словарь с параметрами подключения
        """
        return self.db_config.copy()

    def get_api_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации API.

        Returns:
            Dict[str, Any]: Конфигурация API
        """
        return self.api_config.copy()

    def load_companies(self) -> list:
        """
        Загрузка списка компаний из файла.

        Returns:
            list: Список ID компаний
        """
        try:
            if not self.companies_file.exists():
                print(f"⚠️  Файл {self.companies_file} не найден. Используется список по умолчанию.")
                return self._get_default_companies()

            with open(self.companies_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                companies = data.get('companies', [])

                # Валидация ID компаний
                valid_companies = []
                for company_id in companies:
                    try:
                        valid_id = int(company_id)
                        if valid_id > 0:
                            valid_companies.append(valid_id)
                        else:
                            print(f"⚠️  Некорректный ID компании: {company_id}")
                    except (ValueError, TypeError):
                        print(f"⚠️  Некорректный ID компании: {company_id}")

                if not valid_companies:
                    print("⚠️  Нет валидных ID компаний. Используется список по умолчанию.")
                    return self._get_default_companies()

                return valid_companies

        except json.JSONDecodeError as e:
            print(f"⚠️  Ошибка парсинга JSON: {e}. Используется список по умолчанию.")
            return self._get_default_companies()
        except Exception as e:
            print(f"⚠️  Ошибка загрузки компаний: {e}. Используется список по умолчанию.")
            return self._get_default_companies()

    def _get_default_companies(self) -> list:
        """
        Получение списка компаний по умолчанию.

        Returns:
            list: Список ID компаний
        """
        return [
            1740,  # Яндекс
            3529,  # СберТех
            78638,  # Тинькофф
            3776,  # МТС
            8556,  # VK
            4181,  # Ozon
            1057,  # Avito
            87021,  # Wildberries
            1122462,  # Skyeng
            67611,  # 2ГИС
        ]

    def validate_config(self) -> Dict[str, bool]:
        """
        Проверка конфигурации.

        Returns:
            Dict[str, bool]: Результаты проверки
        """
        checks = {
            'db_host': bool(self.db_config['host']),
            'db_port': self.db_config['port'].isdigit(),
            'db_name': bool(self.db_config['database']),
            'db_user': bool(self.db_config['user']),
            'api_base_url': bool(self.api_config['base_url']),
            'api_timeout': self.api_config['timeout'] > 0,
            'companies_file': self.companies_file.exists()
        }

        return checks