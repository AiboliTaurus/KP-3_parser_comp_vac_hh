"""
Конфигурационный файл для pytest.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def sample_company_data():
    """Фикстура с примером данных компании из API."""
    return {
        "id": "1740",
        "name": "Яндекс",
        "description": "Крупнейшая IT-компания России",
        "site_url": "https://yandex.ru",
        "open_vacancies": 665,
        "trusted": True,
        "accredited_it_employer": True
    }


@pytest.fixture
def sample_processed_company():
    """Фикстура с обработанными данными компании для БД."""
    return {
        'id': 1740,
        'name': 'Яндекс',
        'description': 'Крупнейшая IT-компания России',
        'site_url': 'https://yandex.ru',
        'open_vacancies': 665,
        'trusted': True,
        'accredited_it_employer': True
    }


@pytest.fixture
def sample_vacancy_data():
    """Фикстура с примером данных вакансии из API."""
    return {
        "id": "130573247",
        "name": "Главный бухгалтер в единственном лице",
        "salary": {
            "from": 1600000,
            "to": None,
            "currency": "KZT"
        },
        "alternate_url": "https://hh.ru/vacancy/130573247",
        "employer": {
            "id": "1580604",
            "name": "ВИЗАМЕТРИК"
        },
        "snippet": {
            "requirement": "Высшее экономическое образование",
            "responsibility": "Полное ведение учета"
        },
        "published_at": "2026-02-18T14:57:32+0300",
        "area": {
            "name": "Астана"
        },
        "experience": {
            "name": "Более 6 лет"
        },
        "employment": {
            "name": "Полная занятость"
        },
        "schedule": {
            "name": "Полный день"
        }
    }


@pytest.fixture
def sample_processed_vacancy():
    """Фикстура с обработанными данными вакансии для БД."""
    return {
        'id': '130573247',
        'name': 'Главный бухгалтер в единственном лице',
        'company_id': 1580604,
        'salary_from': 1600000,
        'salary_to': None,
        'currency': 'KZT',
        'avg_salary': 1600000.0,
        'url': 'https://hh.ru/vacancy/130573247',
        'description': 'Требования: Высшее экономическое образование\nОбязанности: Полное ведение учета',
        'published_at': datetime(2026, 2, 18, 14, 57, 32),
        'area': 'Астана',
        'experience': 'Более 6 лет',
        'employment': 'Полная занятость',
        'schedule': 'Полный день'
    }


@pytest.fixture
def sample_vacancies_list():
    """Фикстура со списком вакансий."""
    return [
        {
            "id": "130573247",
            "name": "Главный бухгалтер",
            "salary": {"from": 1600000, "to": None, "currency": "KZT"},
            "employer": {"id": "1580604"}
        },
        {
            "id": "130597510",
            "name": "Бухгалтер",
            "salary": {"from": 1000000, "to": 1000000, "currency": "KZT"},
            "employer": {"id": "12612032"}
        }
    ]


@pytest.fixture
def mock_db_config():
    """Фикстура с конфигурацией БД для тестов."""
    return {
        'host': 'localhost',
        'database': 'test_hh_parser',
        'user': 'postgres',
        'password': 'test_password',
        'port': '5432'
    }


@pytest.fixture
def mock_response():
    """Фикстура для мока ответа requests."""
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json = MagicMock()
    mock.status_code = 200
    return mock


@pytest.fixture
def mock_session(mock_response):
    """Фикстура для мока сессии requests."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session_class.return_value = mock_session
        yield mock_session


@pytest.fixture
def mock_cursor():
    """Фикстура для мока курсора БД."""
    cursor = MagicMock()
    cursor.fetchone = MagicMock()
    cursor.fetchall = MagicMock()
    cursor.rowcount = 0
    return cursor


@pytest.fixture
def mock_db_connection(mock_cursor):
    """Фикстура для мока подключения к БД."""
    conn = MagicMock()
    conn.cursor = MagicMock(return_value=mock_cursor)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    conn.cursor.return_value.__exit__ = MagicMock()
    return conn
