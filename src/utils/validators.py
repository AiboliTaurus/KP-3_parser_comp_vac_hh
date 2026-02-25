"""
Модуль для валидации данных перед вставкой в БД.
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse


class DataValidator:
    """Класс для валидации данных."""

    @staticmethod
    def validate_company_id(company_id: Any) -> Optional[int]:
        """
        Валидация ID компании.

        Args:
            company_id: ID компании для проверки

        Returns:
            Optional[int]: Валидный ID или None
        """
        try:
            # Пробуем преобразовать в int
            if isinstance(company_id, str):
                company_id = int(company_id)
            elif not isinstance(company_id, (int, float)):
                return None

            # Проверяем, что ID положительный
            company_id = int(company_id)
            if company_id <= 0:
                return None

            return company_id
        except (ValueError, TypeError):
            return None

    @staticmethod
    def validate_company_name(name: Any) -> Optional[str]:
        """
        Валидация названия компании.

        Args:
            name: Название для проверки

        Returns:
            Optional[str]: Валидное название или None
        """
        if not name:
            return None

        # Преобразуем в строку
        name = str(name).strip()

        # Проверяем длину
        if len(name) < 1 or len(name) > 255:
            return None

        # Удаляем недопустимые символы (оставляем буквы, цифры, пробелы и базовую пунктуацию)
        cleaned_name = re.sub(r'[^\w\s\-.,&()]', '', name)

        if not cleaned_name:
            return None

        return cleaned_name

    @staticmethod
    def validate_url(url: Any) -> Optional[str]:
        """
        Валидация URL.

        Args:
            url: URL для проверки

        Returns:
            Optional[str]: Валидный URL или None
        """
        if not url:
            return None

        url = str(url).strip()

        try:
            result = urlparse(url)
            # Проверяем, что есть схема и netloc
            if all([result.scheme, result.netloc]):
                # Ограничиваем длину URL
                if len(url) <= 255:
                    return url
        except Exception:
            pass

        return None

    @staticmethod
    def validate_salary(value: Any) -> Optional[int]:
        """
        Валидация зарплаты.

        Args:
            value: Значение зарплаты

        Returns:
            Optional[int]: Валидная зарплата или None
        """
        try:
            if value is None:
                return None

            # Пробуем преобразовать в число
            if isinstance(value, (int, float)):
                salary = int(value)
            elif isinstance(value, str) and value.replace(',', '').replace('.', '').isdigit():
                salary = int(float(value))
            else:
                return None

            # Проверяем диапазон (неотрицательная и не слишком большая)
            if 0 <= salary <= 100_000_000:  # Максимум 100 млн
                return salary
            else:
                return None

        except (ValueError, TypeError):
            return None

    @staticmethod
    def validate_currency(currency: Any) -> Optional[str]:
        """
        Валидация валюты.

        Args:
            currency: Код валюты

        Returns:
            Optional[str]: Валидный код валюты или None
        """
        if not currency:
            return None

        currency = str(currency).strip().upper()

        # Список допустимых валют
        valid_currencies = {'RUB', 'USD', 'EUR', 'KZT', 'UZS', 'BYR', 'BYN'}

        if currency in valid_currencies:
            return currency

        return None

    @staticmethod
    def validate_vacancy_id(vacancy_id: Any) -> Optional[str]:
        """
        Валидация ID вакансии.

        Args:
            vacancy_id: ID вакансии

        Returns:
            Optional[str]: Валидный ID или None
        """
        if not vacancy_id:
            return None

        vacancy_id = str(vacancy_id).strip()

        # ID вакансии должен содержать только цифры
        if vacancy_id.isdigit() and len(vacancy_id) <= 50:
            return vacancy_id

        return None

    @staticmethod
    def validate_date(date_str: Any) -> Optional[datetime]:
        """
        Валидация и парсинг даты.

        Args:
            date_str: Строка с датой

        Returns:
            Optional[datetime]: Объект datetime или None
        """
        if not date_str:
            return None

        try:
            # Пробуем разные форматы
            date_str = str(date_str)

            # Формат с +0300
            if '+0300' in date_str:
                date_str = date_str.replace('+0300', '+03:00')

            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def validate_text(text: Any, max_length: int = 500) -> Optional[str]:
        """
        Валидация текстового поля.

        Args:
            text: Текст для проверки
            max_length: Максимальная длина

        Returns:
            Optional[str]: Валидный текст или None
        """
        if not text:
            return None

        text = str(text).strip()

        # Удаляем лишние пробелы
        text = ' '.join(text.split())

        # Ограничиваем длину
        if len(text) > max_length:
            text = text[:max_length]

        if text:
            return text

        return None

    @staticmethod
    def validate_company_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Комплексная валидация данных компании.

        Args:
            data: Словарь с данными компании

        Returns:
            Dict[str, Any]: Валидированные данные
        """
        validated = {}

        # Валидация ID
        company_id = DataValidator.validate_company_id(data.get('id'))
        if company_id:
            validated['id'] = company_id
        else:
            raise ValueError(f"Некорректный ID компании: {data.get('id')}")

        # Валидация названия
        name = DataValidator.validate_company_name(data.get('name'))
        if name:
            validated['name'] = name
        else:
            validated['name'] = 'Неизвестная компания'

        # Валидация остальных полей (необязательных)
        validated['description'] = DataValidator.validate_text(
            data.get('description'), max_length=1000
        )

        validated['site_url'] = DataValidator.validate_url(data.get('site_url'))

        open_vacancies = DataValidator.validate_salary(data.get('open_vacancies'))
        validated['open_vacancies'] = open_vacancies if open_vacancies is not None else 0

        validated['trusted'] = bool(data.get('trusted', False))
        validated['accredited_it_employer'] = bool(data.get('accredited_it_employer', False))

        return validated

    @staticmethod
    def validate_vacancy_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Комплексная валидация данных вакансии.

        Args:
            data: Словарь с данными вакансии

        Returns:
            Dict[str, Any]: Валидированные данные
        """
        validated = {}

        # Валидация обязательных полей
        vacancy_id = DataValidator.validate_vacancy_id(data.get('id'))
        if vacancy_id:
            validated['id'] = vacancy_id
        else:
            raise ValueError(f"Некорректный ID вакансии: {data.get('id')}")

        name = DataValidator.validate_company_name(data.get('name'))
        if name:
            validated['name'] = name
        else:
            validated['name'] = 'Вакансия'

        company_id = DataValidator.validate_company_id(data.get('company_id'))
        if company_id:
            validated['company_id'] = company_id
        else:
            raise ValueError(f"Некорректный company_id: {data.get('company_id')}")

        # Валидация зарплаты
        validated['salary_from'] = DataValidator.validate_salary(data.get('salary_from'))
        validated['salary_to'] = DataValidator.validate_salary(data.get('salary_to'))
        validated['currency'] = DataValidator.validate_currency(data.get('currency'))

        # Валидация средней зарплаты
        avg_salary = data.get('avg_salary')
        if avg_salary is not None:
            validated['avg_salary'] = DataValidator.validate_salary(avg_salary)
        else:
            validated['avg_salary'] = None

        # Валидация URL
        url = DataValidator.validate_url(data.get('url'))
        if url:
            validated['url'] = url
        else:
            validated['url'] = ''

        # Валидация текстовых полей
        validated['description'] = DataValidator.validate_text(
            data.get('description'), max_length=1000
        )

        validated['area'] = DataValidator.validate_text(data.get('area'), max_length=100)
        validated['experience'] = DataValidator.validate_text(data.get('experience'), max_length=100)
        validated['employment'] = DataValidator.validate_text(data.get('employment'), max_length=100)
        validated['schedule'] = DataValidator.validate_text(data.get('schedule'), max_length=100)

        # Валидация даты
        validated['published_at'] = DataValidator.validate_date(data.get('published_at'))

        return validated

    @staticmethod
    def validate_batch_data(items: List[Dict], validator_func) -> tuple:
        """
        Валидация пакета данных.

        Args:
            items: Список данных для валидации
            validator_func: Функция валидации

        Returns:
            tuple: (валидные данные, ошибки)
        """
        valid_items = []
        errors = []

        for i, item in enumerate(items):
            try:
                valid_item = validator_func(item)
                valid_items.append(valid_item)
            except (ValueError, TypeError) as e:
                errors.append({
                    'index': i,
                    'item': item,
                    'error': str(e)
                })

        return valid_items, errors


# Создаем Pydantic модели для более строгой валидации (опционально)
from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional


class CompanyModel(BaseModel):
    """Pydantic модель для компании."""
    id: int = Field(..., gt=0, description="ID компании")
    name: str = Field(..., min_length=1, max_length=255, description="Название")
    description: Optional[str] = Field(None, max_length=1000)
    site_url: Optional[str] = Field(None, max_length=255)
    open_vacancies: int = Field(0, ge=0)
    trusted: bool = False
    accredited_it_employer: bool = False

    @validator('site_url')
    def validate_site_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            return f'http://{v}'
        return v


class VacancyModel(BaseModel):
    """Pydantic модель для вакансии."""
    id: str = Field(..., min_length=1, max_length=50, pattern=r'^\d+$')
    name: str = Field(..., min_length=1, max_length=255)
    company_id: int = Field(..., gt=0)
    salary_from: Optional[int] = Field(None, ge=0, le=100_000_000)
    salary_to: Optional[int] = Field(None, ge=0, le=100_000_000)
    currency: Optional[str] = Field(None, pattern=r'^(RUB|USD|EUR|KZT|UZS|BYR|BYN)$')
    avg_salary: Optional[float] = Field(None, ge=0, le=100_000_000)
    url: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    published_at: Optional[datetime] = None
    area: Optional[str] = Field(None, max_length=100)
    experience: Optional[str] = Field(None, max_length=100)
    employment: Optional[str] = Field(None, max_length=100)
    schedule: Optional[str] = Field(None, max_length=100)

    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL должен начинаться с http:// или https://')
        return v
