"""
Тесты для модулей работы с базой данных.
Обновлены с учетом текущей структуры проекта.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import psycopg2
from src.db.db_creator import DBCreator
from src.db.database_manager import DBManager


class TestDBCreator:
    """Тесты для класса DBCreator."""

    def test_init(self, mock_db_config):
        """Тест инициализации."""
        creator = DBCreator(mock_db_config)
        assert creator.db_config == mock_db_config
        assert creator.db_name == 'test_hh_parser'

    @patch('psycopg2.connect')
    def test_connect_to_postgres(self, mock_connect, mock_db_config):
        """Тест подключения к системной БД postgres."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        creator = DBCreator(mock_db_config)
        conn = creator._connect_to_postgres()

        assert conn == mock_conn
        mock_connect.assert_called_once_with(
            host='localhost',
            user='postgres',
            password='test_password',
            port='5432',
            database='postgres'
        )

    @patch('psycopg2.connect')
    def test_create_database_new(self, mock_connect, mock_db_config):
        """Тест создания новой БД."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = None  # БД не существует

        creator = DBCreator(mock_db_config)
        result = creator.create_database()

        assert result is True

    @patch('psycopg2.connect')
    def test_create_database_exists(self, mock_connect, mock_db_config):
        """Тест создания БД которая уже существует."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = [1]  # БД существует

        creator = DBCreator(mock_db_config)
        result = creator.create_database()

        assert result is True

    @patch('psycopg2.connect')
    def test_drop_database(self, mock_connect, mock_db_config):
        """Тест удаления БД."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = [1]  # БД существует
        mock_cur.fetchall.return_value = []  # Нет активных подключений

        creator = DBCreator(mock_db_config)

        # Патчим внутренние методы
        with patch.object(creator, '_connect_to_postgres', return_value=mock_conn):
            success, message = creator.drop_database(force=True)

        assert success is True
        assert "успешно удалена" in message

    @patch('psycopg2.connect')
    def test_create_tables(self, mock_connect, mock_db_config):
        """Тест создания таблиц."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        # Важно: настраиваем mock_cur, чтобы он не вызывал ошибок
        mock_cur.execute.return_value = None

        creator = DBCreator(mock_db_config)

        # Вызываем метод
        result = creator.create_tables()

        assert result is True
        # Проверяем, что connect был вызван
        mock_connect.assert_called_once_with(**mock_db_config)
        # Проверяем, что commit был вызван
        mock_conn.commit.assert_called_once()

    @patch('psycopg2.connect')
    def test_clear_tables(self, mock_connect, mock_db_config):
        """Тест очистки таблиц."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        # Важно: настраиваем mock_cur, чтобы он не вызывал ошибок
        mock_cur.execute.return_value = None

        creator = DBCreator(mock_db_config)

        # Вызываем метод
        result = creator.clear_tables()

        assert result is True
        # Проверяем, что connect был вызван
        mock_connect.assert_called_once_with(**mock_db_config)
        # Проверяем, что commit был вызван
        mock_conn.commit.assert_called_once()

    @patch('psycopg2.connect')
    def test_get_database_info(self, mock_connect, mock_db_config):
        """Тест получения информации о БД."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        # Настраиваем возвращаемые значения
        mock_cur.fetchone.side_effect = [
            [1],  # БД существует
            ['10 MB'],  # размер
            [2],  # количество таблиц
            [3]   # активные подключения
        ]

        creator = DBCreator(mock_db_config)

        with patch.object(creator, '_connect_to_postgres', return_value=mock_conn):
            info = creator.get_database_info()

        assert info['name'] == 'test_hh_parser'
        assert info['exists'] is True
        assert info['size'] == '10 MB'
        assert info['tables_count'] == 2
        assert info['active_connections'] == 3


class TestDBManager:
    """Тесты для класса DBManager."""

    def test_init(self, mock_db_config):
        """Тест инициализации."""
        manager = DBManager(mock_db_config)
        assert manager.db_config == mock_db_config
        assert manager.conn is None

    def test_context_manager(self, mock_db_config):
        """Тест контекстного менеджера."""
        with patch.object(DBManager, 'connect') as mock_connect:
            with patch.object(DBManager, 'close') as mock_close:
                with DBManager(mock_db_config) as manager:
                    assert manager is not None
                mock_connect.assert_called_once()
                mock_close.assert_called_once()

    @patch('psycopg2.connect')
    def test_connect_success(self, mock_connect, mock_db_config):
        """Тест успешного подключения к БД."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        manager = DBManager(mock_db_config)
        manager.connect()

        mock_connect.assert_called_once_with(**mock_db_config)
        assert manager.conn == mock_conn

    @patch('psycopg2.connect')
    def test_connect_error(self, mock_connect, mock_db_config):
        """Тест ошибки подключения к БД."""
        mock_connect.side_effect = psycopg2.OperationalError("Connection failed")

        manager = DBManager(mock_db_config)
        with pytest.raises(psycopg2.OperationalError):
            manager.connect()

    def test_close(self, mock_db_config):
        """Тест закрытия подключения."""
        manager = DBManager(mock_db_config)
        mock_conn = MagicMock()
        manager.conn = mock_conn

        manager.close()

        mock_conn.close.assert_called_once()
        assert manager.conn is None

    def test_test_connection_success(self, mock_db_config):
        """Тест успешной проверки подключения."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [1]

        manager = DBManager(mock_db_config)
        manager.conn = MagicMock()
        manager.conn.cursor.return_value.__enter__.return_value = mock_cursor

        result = manager.test_connection()
        assert result is True

    def test_test_connection_failure(self, mock_db_config):
        """Тест неудачной проверки подключения."""
        manager = DBManager(mock_db_config)
        manager.conn = MagicMock()
        manager.conn.cursor.side_effect = Exception("Connection error")

        result = manager.test_connection()
        assert result is False

    @patch('psycopg2.connect')
    def test_execute_query_fetch(self, mock_connect, mock_db_config):
        """Тест выполнения запроса с возвратом результатов."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        expected_results = [{'id': 1, 'name': 'Test'}]
        mock_cur.fetchall.return_value = expected_results

        manager = DBManager(mock_db_config)
        result = manager.execute_query("SELECT * FROM test", fetch=True)

        assert result == expected_results
        mock_cur.execute.assert_called_once_with("SELECT * FROM test", None)

    @patch('psycopg2.connect')
    def test_insert_company_success(self, mock_connect, mock_db_config, sample_processed_company):
        """Тест успешной вставки компании."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        manager = DBManager(mock_db_config)
        manager.conn = mock_conn

        success, error = manager.insert_company(sample_processed_company)

        assert success is True
        assert error is None
        mock_cur.execute.assert_called_once()

    @patch('psycopg2.connect')
    def test_insert_vacancy_success(self, mock_connect, mock_db_config, sample_processed_vacancy):
        """Тест успешной вставки вакансии."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        manager = DBManager(mock_db_config)
        manager.conn = mock_conn

        success, error = manager.insert_vacancy(sample_processed_vacancy)

        assert success is True
        assert error is None
        mock_cur.execute.assert_called_once()

    def test_insert_vacancies_batch(self, mock_db_config):
        """Тест пакетной вставки вакансий."""
        vacancies = [
            {'id': '1', 'name': 'Vacancy 1', 'company_id': 1},
            {'id': '2', 'name': 'Vacancy 2', 'company_id': 1}
        ]

        manager = DBManager(mock_db_config)
        manager.conn = MagicMock()
        manager.insert_vacancy = MagicMock(return_value=(True, None))

        success_count, errors = manager.insert_vacancies_batch(vacancies)

        assert success_count == 2
        assert len(errors) == 0
        assert manager.insert_vacancy.call_count == 2

    @patch('psycopg2.connect')
    def test_get_companies_and_vacancies_count(self, mock_connect, mock_db_config):
        """Тест получения компаний с количеством вакансий."""
        expected = [
            {'id': 1, 'company_name': 'Яндекс', 'vacancies_count': 665},
            {'id': 2, 'company_name': 'СБЕР', 'vacancies_count': 2000}
        ]

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = expected

        manager = DBManager(mock_db_config)
        result = manager.get_companies_and_vacancies_count()

        assert result == expected

    @patch('psycopg2.connect')
    def test_get_all_vacancies(self, mock_connect, mock_db_config):
        """Тест получения всех вакансий."""
        expected = [
            {'id': '1', 'vacancy_name': 'Python Developer', 'company_name': 'Яндекс'},
            {'id': '2', 'vacancy_name': 'Java Developer', 'company_name': 'СБЕР'}
        ]

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = expected

        manager = DBManager(mock_db_config)
        result = manager.get_all_vacancies(limit=10)

        assert result == expected

    @patch('psycopg2.connect')
    def test_get_avg_salary(self, mock_connect, mock_db_config):
        """Тест получения средней зарплаты."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [{'avg_salary': 150000}]

        manager = DBManager(mock_db_config)
        result = manager.get_avg_salary()

        assert result == 150000.0

    @patch('psycopg2.connect')
    def test_get_vacancies_with_higher_salary(self, mock_connect, mock_db_config):
        """Тест получения вакансий с зарплатой выше средней."""
        expected = [
            {'id': '1', 'vacancy_name': 'Senior Developer', 'avg_salary': 300000}
        ]

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = expected

        manager = DBManager(mock_db_config)
        result = manager.get_vacancies_with_higher_salary()

        assert result == expected

    @patch('psycopg2.connect')
    def test_get_vacancies_with_keyword(self, mock_connect, mock_db_config):
        """Тест поиска вакансий по ключевому слову."""
        expected = [
            {'id': '1', 'vacancy_name': 'Python Developer', 'company_name': 'Яндекс'}
        ]

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = expected

        manager = DBManager(mock_db_config)
        result = manager.get_vacancies_with_keyword('python')

        assert result == expected

    @patch('psycopg2.connect')
    def test_get_vacancies_by_area(self, mock_connect, mock_db_config):
        """Тест получения вакансий по региону."""
        expected = [
            {'id': '1', 'vacancy_name': 'Developer', 'area': 'Москва'}
        ]

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = expected

        manager = DBManager(mock_db_config)
        result = manager.get_vacancies_by_area('Москва')

        assert result == expected

    @patch('psycopg2.connect')
    def test_get_companies_stats(self, mock_connect, mock_db_config):
        """Тест получения статистики по компаниям."""
        expected = [
            {
                'company_name': 'Яндекс',
                'total_vacancies': 665,
                'avg_salary': 250000,
                'min_salary': 100000,
                'max_salary': 500000,
                'regions_count': 10,
                'trusted': True,
                'accredited_it_employer': True
            }
        ]

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = expected

        manager = DBManager(mock_db_config)
        result = manager.get_companies_stats()

        assert result == expected

    @patch('psycopg2.connect')
    def test_get_database_stats(self, mock_connect, mock_db_config):
        """Тест получения общей статистики БД."""
        expected = [{
            'total_companies': 10,
            'total_vacancies': 10000,
            'total_areas': 50,
            'overall_avg_salary': 150000,
            'min_avg_salary': 30000,
            'max_avg_salary': 500000
        }]

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = expected

        manager = DBManager(mock_db_config)
        result = manager.get_database_stats()

        assert result == expected[0]
