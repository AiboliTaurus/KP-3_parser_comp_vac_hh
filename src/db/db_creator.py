"""
Модуль для создания и удаления базы данных и таблиц.
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import Dict, Any, Tuple


class DBCreator:
    """Класс для создания и удаления базы данных и таблиц."""

    def __init__(self, db_config: Dict[str, str]):
        """
        Инициализация создателя БД.

        Args:
            db_config (Dict[str, str]): Параметры подключения к БД
        """
        self.db_config = db_config
        self.db_name = db_config['database']

    def _connect_to_postgres(self):
        """
        Подключение к системной БД postgres.

        Returns:
            connection: Объект подключения
        """
        conn = psycopg2.connect(
            host=self.db_config['host'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            port=self.db_config['port'],
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn

    def create_database(self) -> bool:
        """
        Создание базы данных, если она не существует.

        Returns:
            bool: True если успешно создана или уже существует
        """
        try:
            conn = self._connect_to_postgres()
            cur = conn.cursor()

            # Проверяем существует ли БД
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.db_name,))
            exists = cur.fetchone()

            if not exists:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(self.db_name)
                ))
                print(f"✅ База данных {self.db_name} успешно создана")
            else:
                print(f"ℹ️  База данных {self.db_name} уже существует")

            cur.close()
            conn.close()
            return True

        except psycopg2.OperationalError as e:
            print(f"❌ Ошибка подключения к PostgreSQL: {e}")
            return False
        except Exception as e:
            print(f"❌ Ошибка при создании базы данных: {e}")
            return False

    def drop_database(self, force: bool = False) -> Tuple[bool, str]:
        """
        Удаление базы данных.

        Args:
            force (bool): Принудительное удаление без подтверждения

        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        try:
            # Подключаемся к postgres
            conn = self._connect_to_postgres()
            cur = conn.cursor()

            # Проверяем существует ли БД
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.db_name,))
            exists = cur.fetchone()

            if not exists:
                cur.close()
                conn.close()
                return False, f"❌ База данных {self.db_name} не существует"

            # Получаем список активных подключений к БД
            cur.execute("""
                SELECT pid, usename, application_name, client_addr 
                FROM pg_stat_activity 
                WHERE datname = %s
            """, (self.db_name,))

            active_connections = cur.fetchall()

            if active_connections and not force:
                print(f"\n⚠️  Обнаружены активные подключения к базе {self.db_name}:")
                for conn_info in active_connections:
                    print(f"   - PID: {conn_info[0]}, Пользователь: {conn_info[1]}, "
                          f"Приложение: {conn_info[2]}, Адрес: {conn_info[3]}")

                response = input("\nПринудительно закрыть все подключения и удалить БД? (y/n): ")
                if response.lower() != 'y':
                    return False, "❌ Удаление отменено пользователем"
                force = True

            # Принудительно закрываем все подключения к БД
            if force:
                cur.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                """, (self.db_name,))
                terminated = cur.rowcount
                print(f"✅ Закрыто подключений: {terminated}")

            # Удаляем базу данных
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(
                sql.Identifier(self.db_name)
            ))

            cur.close()
            conn.close()

            return True, f"✅ База данных {self.db_name} успешно удалена"

        except Exception as e:
            return False, f"❌ Ошибка при удалении базы данных: {e}"

    def recreate_database(self) -> Tuple[bool, str]:
        """
        Пересоздание базы данных (удалить и создать заново).

        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        print(f"\n⚠️  ВНИМАНИЕ: Будет выполнено пересоздание базы {self.db_name}")
        print("   Все данные будут безвозвратно удалены!")

        response = input("\nПродолжить? (y/n): ").strip().lower()
        if response != 'y':
            return False, "❌ Операция отменена"

        # Удаляем БД
        success, message = self.drop_database(force=True)
        if not success:
            return False, message

        # Создаем БД заново
        if self.create_database():
            if self.create_tables():
                return True, f"✅ База данных {self.db_name} успешно пересоздана"
            else:
                return False, "❌ Ошибка при создании таблиц"
        else:
            return False, "❌ Ошибка при создании базы данных"

    def create_tables(self) -> bool:
        """
        Создание таблиц в базе данных.

        Returns:
            bool: True если таблицы успешно созданы
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            # Создание таблицы компаний
            cur.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    site_url VARCHAR(255),
                    open_vacancies INTEGER DEFAULT 0,
                    trusted BOOLEAN DEFAULT FALSE,
                    accredited_it_employer BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Создание таблицы вакансий
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vacancies (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
                    salary_from INTEGER,
                    salary_to INTEGER,
                    currency VARCHAR(10),
                    avg_salary NUMERIC(10, 2),
                    url VARCHAR(255) NOT NULL,
                    description TEXT,
                    published_at TIMESTAMP,
                    area VARCHAR(100),
                    experience VARCHAR(100),
                    employment VARCHAR(100),
                    schedule VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Создание индексов для ускорения поиска
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_vacancies_company_id ON vacancies(company_id)",
                "CREATE INDEX IF NOT EXISTS idx_vacancies_avg_salary ON vacancies(avg_salary)",
                "CREATE INDEX IF NOT EXISTS idx_vacancies_name ON vacancies(name)",
                "CREATE INDEX IF NOT EXISTS idx_vacancies_area ON vacancies(area)",
                "CREATE INDEX IF NOT EXISTS idx_vacancies_published_at ON vacancies(published_at)",
                "CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name)"
            ]

            for index in indices:
                cur.execute(index)

            conn.commit()
            print("✅ Таблицы успешно созданы")
            cur.close()
            conn.close()
            return True

        except Exception as e:
            print(f"❌ Ошибка при создании таблиц: {e}")
            return False

    def drop_tables(self) -> bool:
        """
        Удаление таблиц.

        Returns:
            bool: True если таблицы успешно удалены
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("""
                DROP TABLE IF EXISTS vacancies CASCADE;
                DROP TABLE IF EXISTS companies CASCADE;
            """)

            conn.commit()
            print("✅ Таблицы успешно удалены")
            cur.close()
            conn.close()
            return True

        except Exception as e:
            print(f"❌ Ошибка при удалении таблиц: {e}")
            return False

    def clear_tables(self) -> bool:
        """
        Очистка таблиц (удаление всех данных без удаления структуры).

        Returns:
            bool: True если таблицы успешно очищены
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("TRUNCATE TABLE vacancies CASCADE;")
            cur.execute("TRUNCATE TABLE companies CASCADE;")

            conn.commit()
            print("✅ Данные в таблицах успешно очищены")
            cur.close()
            conn.close()
            return True

        except Exception as e:
            print(f"❌ Ошибка при очистке таблиц: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """
        Получение информации о базе данных.

        Returns:
            Dict[str, Any]: Информация о БД
        """
        info = {
            'name': self.db_name,
            'exists': False,
            'size': None,
            'tables_count': 0,
            'active_connections': 0
        }

        try:
            conn = self._connect_to_postgres()
            cur = conn.cursor()

            # Проверяем существование
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.db_name,))
            info['exists'] = cur.fetchone() is not None

            if info['exists']:
                # Размер базы данных
                cur.execute("""
                    SELECT pg_size_pretty(pg_database_size(%s)) as size
                """, (self.db_name,))
                result = cur.fetchone()
                info['size'] = result[0] if result else None

                # Количество таблиц
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_catalog = %s
                """, (self.db_name,))
                result = cur.fetchone()
                info['tables_count'] = result[0] if result else 0

                # Активные подключения
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM pg_stat_activity 
                    WHERE datname = %s
                """, (self.db_name,))
                result = cur.fetchone()
                info['active_connections'] = result[0] if result else 0

            cur.close()
            conn.close()

        except Exception as e:
            print(f"❌ Ошибка получения информации о БД: {e}")

        return info
