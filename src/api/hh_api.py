"""
Модуль для взаимодействия с API hh.ru.
Обновлен с улучшенной обработкой ошибок и лимитов API.
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
from ..utils.validators import DataValidator
from ..utils.config import Config


class HH_API:
    """Класс для работы с API HeadHunter."""

    def __init__(self, config: Optional[Config] = None):
        """
        Инициализация клиента API.

        Args:
            config (Optional[Config]): Конфигурация
        """
        self.config = config or Config()
        api_config = self.config.get_api_config()

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HH-User-Agent',
            'Content-Type': 'application/json'
        })

        self.base_url = api_config['base_url']
        self.timeout = api_config['timeout']
        self.max_retries = api_config['max_retries']

        # Константы API hh.ru
        self.MAX_VACANCIES_PER_PAGE = 100
        self.MAX_PAGES = 20  # API hh.ru отдает максимум 2000 вакансий (20 страниц)
        self.RATE_LIMIT_DELAY = 0.5  # Задержка между запросами (сек)

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Выполнение HTTP запроса с повторными попытками и экспоненциальной задержкой.

        Args:
            url (str): URL запроса
            params (Optional[Dict]): Параметры запроса

        Returns:
            Optional[Dict]: Ответ API или None
        """
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )

                # Обработка специфических HTTP ошибок
                if response.status_code == 400:
                    print(f"  ⚠️  API лимит достигнут или неверный запрос (400)")
                    return None
                elif response.status_code == 403:
                    print(f"  ⚠️  Доступ запрещен (403)")
                    return None
                elif response.status_code == 404:
                    print(f"  ⚠️  Ресурс не найден (404)")
                    return None
                elif response.status_code == 429:
                    # Too Many Requests - нужно подождать дольше
                    wait_time = (2 ** attempt) * 2
                    print(f"  ⚠️  Слишком много запросов. Ожидание {wait_time} сек...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.Timeout:
                print(f"  ⚠️  Таймаут запроса. Попытка {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    print(f"  ❌ Превышено количество попыток для URL: {url}")
                    return None
                time.sleep(2 ** attempt)  # Экспоненциальная задержка

            except requests.HTTPError as e:
                if e.response.status_code == 400:
                    # Достигнут лимит API - не повторяем
                    return None
                elif attempt == self.max_retries - 1:
                    print(f"  ❌ HTTP ошибка: {e}")
                    return None
                time.sleep(1)

            except requests.RequestException as e:
                print(f"  ⚠️  Ошибка запроса: {e}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)

        return None

    def get_company(self, company_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение информации о компании по ID.

        Args:
            company_id (int): ID компании на hh.ru

        Returns:
            Optional[Dict[str, Any]]: Данные о компании или None при ошибке
        """
        valid_id = DataValidator.validate_company_id(company_id)
        if not valid_id:
            print(f"  ❌ Некорректный ID компании: {company_id}")
            return None

        url = f"{self.base_url}employers/{valid_id}"
        return self._make_request(url)

    def search_companies(self, text: str = "", area: Optional[int] = None,
                        page: int = 0, per_page: int = 20) -> List[Dict[str, Any]]:
        """
        Поиск компаний по тексту.

        Args:
            text (str): Текст для поиска
            area (Optional[int]): ID региона
            page (int): Номер страницы
            per_page (int): Количество на странице

        Returns:
            List[Dict[str, Any]]: Список компаний
        """
        if per_page < 1 or per_page > 100:
            per_page = 20
        if page < 0:
            page = 0

        params = {
            'text': text,
            'page': page,
            'per_page': per_page
        }
        if area and DataValidator.validate_company_id(area):
            params['area'] = area

        url = f"{self.base_url}employers"
        result = self._make_request(url, params)

        if result and isinstance(result, dict):
            return result.get('items', [])
        return []

    def get_vacancies(self, employer_id: int, page: int = 0, per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Получение вакансий компании.

        Args:
            employer_id (int): ID компании
            page (int): Номер страницы
            per_page (int): Количество вакансий на странице

        Returns:
            List[Dict[str, Any]]: Список вакансий
        """
        valid_id = DataValidator.validate_company_id(employer_id)
        if not valid_id:
            print(f"  ❌ Некорректный ID компании: {employer_id}")
            return []

        if per_page < 1 or per_page > 100:
            per_page = 100
        if page < 0:
            page = 0

        # Проверка на превышение лимита API
        if page >= self.MAX_PAGES:
            print(f"  ℹ️  Достигнут максимальный номер страницы ({self.MAX_PAGES})")
            return []

        params = {
            'employer_id': valid_id,
            'page': page,
            'per_page': per_page
        }

        url = f"{self.base_url}vacancies"
        result = self._make_request(url, params)

        if result and isinstance(result, dict):
            return result.get('items', [])
        return []

    def get_all_company_vacancies(self, company_id: int) -> List[Dict[str, Any]]:
        """
        Получение всех вакансий компании с учетом лимитов API.

        Args:
            company_id (int): ID компании

        Returns:
            List[Dict[str, Any]]: Список всех доступных вакансий
        """
        valid_id = DataValidator.validate_company_id(company_id)
        if not valid_id:
            return []

        all_vacancies = []
        page = 0
        max_retries = 3

        print(f"  📥 Загрузка вакансий...")

        while page < self.MAX_PAGES:
            for attempt in range(max_retries):
                try:
                    vacancies = self.get_vacancies(valid_id, page)

                    if not vacancies:
                        # Пустая страница - значит достигли конца
                        print(f"  ✅ Загружено страниц: {page}")
                        return all_vacancies

                    all_vacancies.extend(vacancies)

                    # Показываем прогресс
                    print(f"     Страница {page + 1}: +{len(vacancies)} вакансий (всего: {len(all_vacancies)})")

                    # Если получили меньше чем запрашивали - это последняя страница
                    if len(vacancies) < self.MAX_VACANCIES_PER_PAGE:
                        return all_vacancies

                    break  # Успешно получили, выходим из цикла retry

                except requests.HTTPError as e:
                    if e.response.status_code == 400:
                        # Достигнут лимит API
                        print(f"  ℹ️  Достигнут лимит API для компании {company_id} на странице {page}")
                        return all_vacancies
                    elif attempt == max_retries - 1:
                        print(f"  ⚠️  Не удалось получить страницу {page} после {max_retries} попыток")
                        return all_vacancies
                    time.sleep(1)

                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"  ⚠️  Ошибка на странице {page}: {e}")
                        return all_vacancies
                    time.sleep(1)

            page += 1
            time.sleep(self.RATE_LIMIT_DELAY)  # Задержка между страницами

        print(f"  ✅ Достигнут лимит API в {self.MAX_PAGES * self.MAX_VACANCIES_PER_PAGE} вакансий")
        return all_vacancies

    def process_company_data(self, company_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обработка данных компании для сохранения в БД.

        Args:
            company_data (Dict[str, Any]): Данные компании из API

        Returns:
            Optional[Dict[str, Any]]: Обработанные данные компании
        """
        if not company_data:
            return None

        try:
            raw_data = {
                'id': company_data.get('id'),
                'name': company_data.get('name'),
                'description': company_data.get('description', ''),
                'site_url': company_data.get('site_url', ''),
                'open_vacancies': company_data.get('open_vacancies', 0),
                'trusted': company_data.get('trusted', False),
                'accredited_it_employer': company_data.get('accredited_it_employer', False)
            }

            validated_data = DataValidator.validate_company_data(raw_data)
            return validated_data

        except ValueError as e:
            print(f"  ❌ Ошибка валидации данных компании: {e}")
            return None
        except Exception as e:
            print(f"  ❌ Непредвиденная ошибка при обработке компании: {e}")
            return None

    def process_vacancy_data(self, vacancy_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обработка данных вакансии для сохранения в БД.

        Args:
            vacancy_data (Dict[str, Any]): Данные вакансии из API

        Returns:
            Optional[Dict[str, Any]]: Обработанные данные вакансии
        """
        if not vacancy_data:
            return None

        try:
            # Обработка зарплаты
            salary = vacancy_data.get('salary')
            salary_from = None
            salary_to = None
            currency = None
            avg_salary = None

            if salary and isinstance(salary, dict):
                salary_from = salary.get('from')
                salary_to = salary.get('to')
                currency = salary.get('currency')

                # Расчет средней зарплаты
                if salary_from is not None and salary_to is not None:
                    avg_salary = (salary_from + salary_to) / 2
                elif salary_from is not None:
                    avg_salary = float(salary_from)
                elif salary_to is not None:
                    avg_salary = float(salary_to)

            # Получение employer_id
            employer = vacancy_data.get('employer', {})
            company_id = employer.get('id')

            # Обработка описания
            snippet = vacancy_data.get('snippet', {})
            requirement = snippet.get('requirement', '')
            responsibility = snippet.get('responsibility', '')
            description = f"Требования: {requirement}\nОбязанности: {responsibility}" if requirement or responsibility else ''

            raw_data = {
                'id': vacancy_data.get('id'),
                'name': vacancy_data.get('name'),
                'company_id': company_id,
                'salary_from': salary_from,
                'salary_to': salary_to,
                'currency': currency,
                'avg_salary': avg_salary,
                'url': vacancy_data.get('alternate_url', ''),
                'description': description,
                'published_at': vacancy_data.get('published_at'),
                'area': vacancy_data.get('area', {}).get('name'),
                'experience': vacancy_data.get('experience', {}).get('name'),
                'employment': vacancy_data.get('employment', {}).get('name'),
                'schedule': vacancy_data.get('schedule', {}).get('name')
            }

            validated_data = DataValidator.validate_vacancy_data(raw_data)
            return validated_data

        except ValueError as e:
            print(f"  ⚠️  Ошибка валидации вакансии {vacancy_data.get('id')}: {e}")
            return None
        except Exception as e:
            print(f"  ⚠️  Непредвиденная ошибка при обработке вакансии: {e}")
            return None

    def process_company_vacancies(self, company_id: int) -> List[Dict[str, Any]]:
        """
        Обработка всех вакансий компании.

        Args:
            company_id (int): ID компании

        Returns:
            List[Dict[str, Any]]: Список обработанных вакансий
        """
        valid_id = DataValidator.validate_company_id(company_id)
        if not valid_id:
            return []

        vacancies = self.get_all_company_vacancies(valid_id)
        processed_vacancies = []
        errors = 0

        for i, vacancy in enumerate(vacancies):
            processed = self.process_vacancy_data(vacancy)
            if processed:
                processed_vacancies.append(processed)
            else:
                errors += 1

            # Показываем прогресс каждые 100 вакансий
            if (i + 1) % 100 == 0:
                print(f"     Обработано {i + 1}/{len(vacancies)} вакансий...")

        if errors > 0:
            print(f"  ⚠️  Пропущено {errors} вакансий из-за ошибок валидации")

        return processed_vacancies
