"""
Модуль для работы с данными в базе данных.
Расширенная версия с улучшенным поиском по регионам и дополнительными методами.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from typing import List, Dict, Any, Optional, Tuple
from ..utils.validators import DataValidator


class DBManager:
    """Класс для управления данными в базе данных."""

    def __init__(self, db_config: Dict[str, str]):
        """
        Инициализация менеджера БД.

        Args:
            db_config (Dict[str, str]): Параметры подключения к БД
        """
        self.db_config = db_config
        self.conn = None

    def __enter__(self):
        """Контекстный менеджер для подключения."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие подключения при выходе из контекста."""
        self.close()

    def connect(self):
        """Установка соединения с БД."""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.conn.autocommit = False
        except psycopg2.OperationalError as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            print("Проверьте:")
            print("  - Запущен ли PostgreSQL")
            print("  - Правильность параметров в .env файле")
            print("  - Доступность базы данных")
            raise
        except Exception as e:
            print(f"❌ Непредвиденная ошибка подключения: {e}")
            raise

    def close(self):
        """Закрытие соединения с БД."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def test_connection(self) -> bool:
        """
        Тестирование подключения к БД.

        Returns:
            bool: True если подключение работает
        """
        try:
            if not self.conn:
                self.connect()

            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                return result[0] == 1
        except Exception as e:
            print(f"❌ Ошибка тестирования подключения: {e}")
            return False

    def execute_query(self, query: str, params: Optional[tuple] = None,
                     fetch: bool = True) -> Optional[List[Dict]]:
        """
        Выполнение SQL запроса.

        Args:
            query (str): SQL запрос
            params (Optional[tuple]): Параметры запроса
            fetch (bool): Нужно ли возвращать результаты

        Returns:
            Optional[List[Dict]]: Результаты запроса или None
        """
        if not self.conn:
            self.connect()

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)

                if fetch:
                    results = cur.fetchall()
                    return [dict(row) for row in results]

                self.conn.commit()
                return None

        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"❌ Ошибка выполнения запроса: {e}")
            print(f"Запрос: {query[:200]}...")
            raise
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Непредвиденная ошибка: {e}")
            raise

    def insert_company(self, company_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Вставка данных компании в БД с валидацией.

        Args:
            company_data (Dict[str, Any]): Данные компании

        Returns:
            Tuple[bool, Optional[str]]: (успех, сообщение об ошибке)
        """
        try:
            # Валидация данных
            validated_data = DataValidator.validate_company_data(company_data)

            query = """
                INSERT INTO companies (
                    id, name, description, site_url, open_vacancies, 
                    trusted, accredited_it_employer
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    site_url = EXCLUDED.site_url,
                    open_vacancies = EXCLUDED.open_vacancies,
                    trusted = EXCLUDED.trusted,
                    accredited_it_employer = EXCLUDED.accredited_it_employer
            """
            params = (
                validated_data['id'],
                validated_data['name'],
                validated_data.get('description', ''),
                validated_data.get('site_url', ''),
                validated_data.get('open_vacancies', 0),
                validated_data.get('trusted', False),
                validated_data.get('accredited_it_employer', False)
            )
            self.execute_query(query, params, fetch=False)
            return True, None

        except ValueError as e:
            error_msg = f"Ошибка валидации: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Ошибка вставки: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def insert_vacancy(self, vacancy_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Вставка данных вакансии в БД с валидацией.

        Args:
            vacancy_data (Dict[str, Any]): Данные вакансии

        Returns:
            Tuple[bool, Optional[str]]: (успех, сообщение об ошибке)
        """
        try:
            # Валидация данных
            validated_data = DataValidator.validate_vacancy_data(vacancy_data)

            query = """
                INSERT INTO vacancies (
                    id, name, company_id, salary_from, salary_to,
                    currency, avg_salary, url, description, published_at,
                    area, experience, employment, schedule
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    salary_from = EXCLUDED.salary_from,
                    salary_to = EXCLUDED.salary_to,
                    currency = EXCLUDED.currency,
                    avg_salary = EXCLUDED.avg_salary,
                    url = EXCLUDED.url,
                    description = EXCLUDED.description,
                    published_at = EXCLUDED.published_at,
                    area = EXCLUDED.area,
                    experience = EXCLUDED.experience,
                    employment = EXCLUDED.employment,
                    schedule = EXCLUDED.schedule
            """
            params = (
                validated_data['id'],
                validated_data['name'],
                validated_data['company_id'],
                validated_data.get('salary_from'),
                validated_data.get('salary_to'),
                validated_data.get('currency'),
                validated_data.get('avg_salary'),
                validated_data.get('url', ''),
                validated_data.get('description', ''),
                validated_data.get('published_at'),
                validated_data.get('area'),
                validated_data.get('experience'),
                validated_data.get('employment'),
                validated_data.get('schedule')
            )
            self.execute_query(query, params, fetch=False)
            return True, None

        except ValueError as e:
            error_msg = f"Ошибка валидации вакансии {vacancy_data.get('id')}: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Ошибка вставки вакансии {vacancy_data.get('id')}: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def insert_vacancies_batch(self, vacancies: List[Dict[str, Any]]) -> Tuple[int, List[Dict]]:
        """
        Пакетная вставка вакансий с валидацией.

        Args:
            vacancies (List[Dict[str, Any]]): Список вакансий

        Returns:
            Tuple[int, List[Dict]]: (количество успешных, список ошибок)
        """
        success_count = 0
        errors = []

        for i, vacancy in enumerate(vacancies):
            success, error = self.insert_vacancy(vacancy)
            if success:
                success_count += 1
            else:
                errors.append({
                    'index': i,
                    'vacancy_id': vacancy.get('id'),
                    'error': error
                })

            # Коммитим каждые 100 записей
            if (i + 1) % 100 == 0:
                self.conn.commit()

        # Финальный коммит
        self.conn.commit()

        return success_count, errors

    def get_companies_and_vacancies_count(self) -> List[Dict[str, Any]]:
        """
        Получает список всех компаний и количество вакансий у каждой компании.

        Returns:
            List[Dict[str, Any]]: Список компаний с количеством вакансий
        """
        query = """
            SELECT 
                c.id,
                c.name as company_name,
                COUNT(v.id) as vacancies_count,
                c.open_vacancies as hh_vacancies_count,
                c.trusted,
                c.accredited_it_employer
            FROM companies c
            LEFT JOIN vacancies v ON c.id = v.company_id
            GROUP BY c.id, c.name, c.open_vacancies, c.trusted, c.accredited_it_employer
            ORDER BY vacancies_count DESC, c.name
        """
        return self.execute_query(query) or []

    def get_all_vacancies(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получает список всех вакансий.

        Args:
            limit (Optional[int]): Ограничение количества записей

        Returns:
            List[Dict[str, Any]]: Список вакансий
        """
        query = """
            SELECT 
                v.id,
                v.name as vacancy_name,
                c.name as company_name,
                v.salary_from,
                v.salary_to,
                v.currency,
                v.avg_salary,
                v.url,
                v.published_at,
                v.area,
                v.experience,
                v.employment,
                v.schedule
            FROM vacancies v
            JOIN companies c ON v.company_id = c.id
            ORDER BY v.published_at DESC
        """

        if limit and limit > 0:
            query += f" LIMIT {limit}"

        return self.execute_query(query) or []

    def get_avg_salary(self) -> float:
        """
        Получает среднюю зарплату по вакансиям.

        Returns:
            float: Средняя зарплата
        """
        query = """
            SELECT COALESCE(ROUND(AVG(avg_salary), 2), 0) as avg_salary
            FROM vacancies
            WHERE avg_salary IS NOT NULL AND avg_salary > 0
        """
        result = self.execute_query(query)
        return float(result[0]['avg_salary']) if result and result[0] else 0.0

    def get_vacancies_with_higher_salary(self) -> List[Dict[str, Any]]:
        """
        Получает список всех вакансий, у которых зарплата выше средней.

        Returns:
            List[Dict[str, Any]]: Список вакансий с зарплатой выше средней
        """
        query = """
            SELECT 
                v.id,
                v.name as vacancy_name,
                c.name as company_name,
                v.salary_from,
                v.salary_to,
                v.avg_salary,
                v.currency,
                v.url,
                v.area,
                v.experience
            FROM vacancies v
            JOIN companies c ON v.company_id = c.id
            WHERE v.avg_salary > (SELECT COALESCE(AVG(avg_salary), 0) FROM vacancies WHERE avg_salary IS NOT NULL)
            ORDER BY v.avg_salary DESC
        """
        return self.execute_query(query) or []

    def get_vacancies_with_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Получает список всех вакансий, в названии которых содержатся переданные слова.

        Args:
            keyword (str): Ключевое слово для поиска

        Returns:
            List[Dict[str, Any]]: Список вакансий, содержащих ключевое слово
        """
        if not keyword or not isinstance(keyword, str):
            return []

        # Очистка ключевого слова
        keyword = keyword.strip()
        if len(keyword) < 2:
            return []

        query = """
            SELECT 
                v.id,
                v.name as vacancy_name,
                c.name as company_name,
                v.salary_from,
                v.salary_to,
                v.avg_salary,
                v.currency,
                v.url,
                v.area,
                v.experience,
                v.description
            FROM vacancies v
            JOIN companies c ON v.company_id = c.id
            WHERE 
                LOWER(v.name) LIKE LOWER(%s) OR 
                LOWER(v.description) LIKE LOWER(%s) OR
                LOWER(v.area) LIKE LOWER(%s)
            ORDER BY 
                CASE 
                    WHEN LOWER(v.name) LIKE LOWER(%s) THEN 1
                    WHEN LOWER(v.description) LIKE LOWER(%s) THEN 2
                    ELSE 3
                END,
                v.published_at DESC
        """
        search_pattern = f'%{keyword}%'
        return self.execute_query(
            query,
            (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern)
        ) or []

    # ============= УЛУЧШЕННЫЕ МЕТОДЫ =============

    def get_vacancies_by_area(self, area: str, exact_match: bool = False) -> List[Dict[str, Any]]:
        """
        Получает список вакансий по региону (поддерживает названия и коды).

        Args:
            area (str): Название региона или код (например: "Москва", "01", "77")
            exact_match (bool): Точное совпадение (True) или частичное (False)

        Returns:
            List[Dict[str, Any]]: Список вакансий в указанном регионе
        """
        if not area:
            return []

        area = area.strip()
        if len(area) < 2:
            return []

        # Определяем тип поиска
        if exact_match:
            # Точное совпадение
            query = """
                SELECT 
                    v.id,
                    v.name as vacancy_name,
                    c.name as company_name,
                    v.salary_from,
                    v.salary_to,
                    v.avg_salary,
                    v.currency,
                    v.url,
                    v.area
                FROM vacancies v
                JOIN companies c ON v.company_id = c.id
                WHERE LOWER(v.area) = LOWER(%s) OR v.area = %s
                ORDER BY v.published_at DESC
            """
            return self.execute_query(query, (area, area)) or []
        else:
            # Частичное совпадение (по умолчанию)
            query = """
                SELECT 
                    v.id,
                    v.name as vacancy_name,
                    c.name as company_name,
                    v.salary_from,
                    v.salary_to,
                    v.avg_salary,
                    v.currency,
                    v.url,
                    v.area
                FROM vacancies v
                JOIN companies c ON v.company_id = c.id
                WHERE 
                    LOWER(v.area) LIKE LOWER(%s) OR
                    v.area LIKE %s
                ORDER BY 
                    CASE 
                        WHEN LOWER(v.area) = LOWER(%s) THEN 1
                        WHEN LOWER(v.area) LIKE LOWER(%s) THEN 2
                        ELSE 3
                    END,
                    v.published_at DESC
            """
            pattern = f'%{area}%'
            return self.execute_query(query, (pattern, pattern, area, pattern)) or []

    def get_companies_by_vacancies_count(self, min_vacancies: int = 0) -> List[Dict[str, Any]]:
        """
        Получает компании с количеством вакансий больше указанного.

        Args:
            min_vacancies (int): Минимальное количество вакансий

        Returns:
            List[Dict[str, Any]]: Список компаний
        """
        query = """
            SELECT 
                c.id,
                c.name as company_name,
                COUNT(v.id) as vacancies_count,
                c.open_vacancies as hh_vacancies_count,
                c.trusted,
                c.accredited_it_employer
            FROM companies c
            LEFT JOIN vacancies v ON c.id = v.company_id
            GROUP BY c.id, c.name, c.open_vacancies, c.trusted, c.accredited_it_employer
            HAVING COUNT(v.id) >= %s
            ORDER BY vacancies_count DESC
        """
        return self.execute_query(query, (min_vacancies,)) or []

    def get_top_regions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает топ регионов по количеству вакансий.

        Args:
            limit (int): Количество регионов

        Returns:
            List[Dict[str, Any]]: Список регионов с количеством вакансий
        """
        query = """
            SELECT 
                area,
                COUNT(*) as vacancies_count,
                ROUND(AVG(avg_salary), 2) as avg_salary,
                MIN(avg_salary) as min_salary,
                MAX(avg_salary) as max_salary
            FROM vacancies
            WHERE area IS NOT NULL AND area != ''
            GROUP BY area
            ORDER BY vacancies_count DESC
            LIMIT %s
        """
        return self.execute_query(query, (limit,)) or []

    def get_salary_statistics_by_experience(self) -> List[Dict[str, Any]]:
        """
        Получает статистику зарплат по уровню опыта.

        Returns:
            List[Dict[str, Any]]: Статистика по группам опыта
        """
        query = """
            SELECT 
                experience,
                COUNT(*) as vacancies_count,
                ROUND(AVG(avg_salary), 2) as avg_salary,
                MIN(avg_salary) as min_salary,
                MAX(avg_salary) as max_salary
            FROM vacancies
            WHERE experience IS NOT NULL AND avg_salary IS NOT NULL
            GROUP BY experience
            ORDER BY 
                CASE experience
                    WHEN 'Нет опыта' THEN 1
                    WHEN 'От 1 года до 3 лет' THEN 2
                    WHEN 'От 3 до 6 лет' THEN 3
                    WHEN 'Более 6 лет' THEN 4
                    ELSE 5
                END
        """
        return self.execute_query(query) or []

    def search_vacancies_advanced(self, **filters) -> List[Dict[str, Any]]:
        """
        Расширенный поиск вакансий с множеством фильтров.

        Args:
            **filters: Словарь с фильтрами
                - keyword (str): Ключевое слово
                - area (str): Регион
                - company_id (int): ID компании
                - salary_min (int): Минимальная зарплата
                - salary_max (int): Максимальная зарплата
                - experience (str): Требуемый опыт
                - employment (str): Тип занятости
                - schedule (str): График работы
                - limit (int): Лимит записей

        Returns:
            List[Dict[str, Any]]: Список вакансий
        """
        conditions = []
        params = []
        param_index = 1

        # Базовый запрос
        query = """
            SELECT 
                v.id,
                v.name as vacancy_name,
                c.name as company_name,
                v.salary_from,
                v.salary_to,
                v.avg_salary,
                v.currency,
                v.url,
                v.area,
                v.experience,
                v.employment,
                v.schedule,
                v.description
            FROM vacancies v
            JOIN companies c ON v.company_id = c.id
            WHERE 1=1
        """

        # Добавление фильтров
        if filters.get('keyword'):
            conditions.append(f"(LOWER(v.name) LIKE LOWER($${param_index}$$) OR LOWER(v.description) LIKE LOWER($${param_index}$$))")
            params.append(f'%{filters["keyword"]}%')
            param_index += 1

        if filters.get('area'):
            conditions.append(f"(LOWER(v.area) LIKE LOWER($${param_index}$$) OR v.area LIKE $${param_index}$$)")
            params.append(f'%{filters["area"]}%')
            param_index += 1

        if filters.get('company_id'):
            conditions.append(f"v.company_id = $${param_index}$$")
            params.append(filters['company_id'])
            param_index += 1

        if filters.get('salary_min'):
            conditions.append(f"v.avg_salary >= $${param_index}$$")
            params.append(filters['salary_min'])
            param_index += 1

        if filters.get('salary_max'):
            conditions.append(f"v.avg_salary <= $${param_index}$$")
            params.append(filters['salary_max'])
            param_index += 1

        if filters.get('experience'):
            conditions.append(f"LOWER(v.experience) = LOWER($${param_index}$$)")
            params.append(filters['experience'])
            param_index += 1

        if filters.get('employment'):
            conditions.append(f"LOWER(v.employment) LIKE LOWER($${param_index}$$)")
            params.append(f'%{filters["employment"]}%')
            param_index += 1

        if filters.get('schedule'):
            conditions.append(f"LOWER(v.schedule) LIKE LOWER($${param_index}$$)")
            params.append(f'%{filters["schedule"]}%')
            param_index += 1

        # Добавляем условия в запрос
        if conditions:
            query += " AND " + " AND ".join(conditions)

        # Сортировка
        query += " ORDER BY v.published_at DESC"

        # Лимит
        if filters.get('limit'):
            query += f" LIMIT {filters['limit']}"

        # Заменяем $$ на %s для psycopg2
        query = query.replace('$$', '%')

        return self.execute_query(query, tuple(params) if params else None) or []

    def get_companies_and_vacancies_count(self) -> List[Dict[str, Any]]:
        """
        Получает список всех компаний и количество вакансий у каждой компании.

        Returns:
            List[Dict[str, Any]]: Список компаний с количеством вакансий
        """
        query = """
            SELECT 
                c.id,
                c.name as company_name,
                COUNT(v.id) as vacancies_count,
                c.open_vacancies as hh_vacancies_count,
                c.trusted,
                c.accredited_it_employer
            FROM companies c
            LEFT JOIN vacancies v ON c.id = v.company_id
            GROUP BY c.id, c.name, c.open_vacancies, c.trusted, c.accredited_it_employer
            ORDER BY vacancies_count DESC, c.name
        """
        return self.execute_query(query) or []

    def get_all_vacancies(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получает список всех вакансий.

        Args:
            limit (Optional[int]): Ограничение количества записей

        Returns:
            List[Dict[str, Any]]: Список вакансий
        """
        query = """
            SELECT 
                v.id,
                v.name as vacancy_name,
                c.name as company_name,
                v.salary_from,
                v.salary_to,
                v.currency,
                v.avg_salary,
                v.url,
                v.published_at,
                v.area,
                v.experience,
                v.employment,
                v.schedule
            FROM vacancies v
            JOIN companies c ON v.company_id = c.id
            ORDER BY v.published_at DESC
        """

        if limit and limit > 0:
            query += f" LIMIT {limit}"

        return self.execute_query(query) or []

    def get_avg_salary(self) -> float:
        """
        Получает среднюю зарплату по вакансиям.

        Returns:
            float: Средняя зарплата
        """
        query = """
            SELECT COALESCE(ROUND(AVG(avg_salary), 2), 0) as avg_salary
            FROM vacancies
            WHERE avg_salary IS NOT NULL AND avg_salary > 0
        """
        result = self.execute_query(query)
        return float(result[0]['avg_salary']) if result and result[0] else 0.0

    def get_vacancies_with_higher_salary(self) -> List[Dict[str, Any]]:
        """
        Получает список всех вакансий, у которых зарплата выше средней.

        Returns:
            List[Dict[str, Any]]: Список вакансий с зарплатой выше средней
        """
        query = """
            SELECT 
                v.id,
                v.name as vacancy_name,
                c.name as company_name,
                v.salary_from,
                v.salary_to,
                v.avg_salary,
                v.currency,
                v.url,
                v.area,
                v.experience
            FROM vacancies v
            JOIN companies c ON v.company_id = c.id
            WHERE v.avg_salary > (SELECT COALESCE(AVG(avg_salary), 0) FROM vacancies WHERE avg_salary IS NOT NULL)
            ORDER BY v.avg_salary DESC
        """
        return self.execute_query(query) or []

    def get_vacancies_with_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Получает список всех вакансий, в названии которых содержатся переданные слова.

        Args:
            keyword (str): Ключевое слово для поиска

        Returns:
            List[Dict[str, Any]]: Список вакансий, содержащих ключевое слово
        """
        if not keyword or not isinstance(keyword, str):
            return []

        # Очистка ключевого слова
        keyword = keyword.strip()
        if len(keyword) < 2:
            return []

        query = """
            SELECT 
                v.id,
                v.name as vacancy_name,
                c.name as company_name,
                v.salary_from,
                v.salary_to,
                v.avg_salary,
                v.currency,
                v.url,
                v.area,
                v.experience,
                v.description
            FROM vacancies v
            JOIN companies c ON v.company_id = c.id
            WHERE 
                LOWER(v.name) LIKE LOWER(%s) OR 
                LOWER(v.description) LIKE LOWER(%s) OR
                LOWER(v.area) LIKE LOWER(%s)
            ORDER BY 
                CASE 
                    WHEN LOWER(v.name) LIKE LOWER(%s) THEN 1
                    WHEN LOWER(v.description) LIKE LOWER(%s) THEN 2
                    ELSE 3
                END,
                v.published_at DESC
        """
        search_pattern = f'%{keyword}%'
        return self.execute_query(
            query,
            (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern)
        ) or []

    # ============= УЛУЧШЕННЫЙ МЕТОД ПОИСКА ПО РЕГИОНУ =============

    def get_vacancies_by_area(self, area: str, exact_match: bool = False) -> List[Dict[str, Any]]:
        """
        Получает список вакансий по региону (поддерживает названия и коды).

        Args:
            area (str): Название региона или код (например: "Москва", "01", "77")
            exact_match (bool): Точное совпадение (True) или частичное (False)

        Returns:
            List[Dict[str, Any]]: Список вакансий в указанном регионе
        """
        if not area:
            return []

        area = area.strip()
        if len(area) < 2:
            return []

        # Определяем тип поиска
        if exact_match:
            # Точное совпадение
            query = """
                SELECT 
                    v.id,
                    v.name as vacancy_name,
                    c.name as company_name,
                    v.salary_from,
                    v.salary_to,
                    v.avg_salary,
                    v.currency,
                    v.url,
                    v.area
                FROM vacancies v
                JOIN companies c ON v.company_id = c.id
                WHERE LOWER(v.area) = LOWER(%s) OR v.area = %s
                ORDER BY v.published_at DESC
            """
            return self.execute_query(query, (area, area)) or []
        else:
            # Частичное совпадение (по умолчанию)
            query = """
                SELECT 
                    v.id,
                    v.name as vacancy_name,
                    c.name as company_name,
                    v.salary_from,
                    v.salary_to,
                    v.avg_salary,
                    v.currency,
                    v.url,
                    v.area
                FROM vacancies v
                JOIN companies c ON v.company_id = c.id
                WHERE 
                    LOWER(v.area) LIKE LOWER(%s) OR
                    v.area LIKE %s
                ORDER BY 
                    CASE 
                        WHEN LOWER(v.area) = LOWER(%s) THEN 1
                        WHEN LOWER(v.area) LIKE LOWER(%s) THEN 2
                        ELSE 3
                    END,
                    v.published_at DESC
            """
            pattern = f'%{area}%'
            return self.execute_query(query, (pattern, pattern, area, pattern)) or []

    def get_companies_stats(self) -> List[Dict[str, Any]]:
        """
        Получает статистику по компаниям.

        Returns:
            List[Dict[str, Any]]: Статистика по компаниям
        """
        query = """
            SELECT 
                c.name as company_name,
                COUNT(v.id) as total_vacancies,
                ROUND(COALESCE(AVG(v.avg_salary), 0), 2) as avg_salary,
                MIN(v.salary_from) as min_salary,
                MAX(v.salary_to) as max_salary,
                COUNT(DISTINCT v.area) as regions_count,
                c.trusted,
                c.accredited_it_employer
            FROM companies c
            LEFT JOIN vacancies v ON c.id = v.company_id
            GROUP BY c.id, c.name, c.trusted, c.accredited_it_employer
            HAVING COUNT(v.id) > 0
            ORDER BY total_vacancies DESC
        """
        return self.execute_query(query) or []

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Получает общую статистику по базе данных.

        Returns:
            Dict[str, Any]: Статистика БД
        """
        query = """
            SELECT 
                (SELECT COUNT(*) FROM companies) as total_companies,
                (SELECT COUNT(*) FROM vacancies) as total_vacancies,
                (SELECT COUNT(DISTINCT area) FROM vacancies WHERE area IS NOT NULL) as total_areas,
                (SELECT ROUND(AVG(avg_salary), 2) FROM vacancies WHERE avg_salary IS NOT NULL) as overall_avg_salary,
                (SELECT MIN(avg_salary) FROM vacancies WHERE avg_salary IS NOT NULL) as min_avg_salary,
                (SELECT MAX(avg_salary) FROM vacancies WHERE avg_salary IS NOT NULL) as max_avg_salary
        """
        result = self.execute_query(query)
        return result[0] if result else {}
