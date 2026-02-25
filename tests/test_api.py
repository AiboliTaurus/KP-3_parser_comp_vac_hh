"""
Тесты для модуля работы с API hh.ru.
Обновлены с учетом текущей структуры проекта.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
import requests
from src.api.hh_api import HH_API


class TestHHAPI:
    """Тесты для класса HH_API."""

    def test_init(self, mock_db_config):
        """Тест инициализации."""
        with patch('src.api.hh_api.Config') as mock_config:
            mock_config.return_value.get_api_config.return_value = {
                'base_url': 'https://api.hh.ru/',
                'timeout': 30,
                'max_retries': 3
            }
            api = HH_API()
            assert api.base_url == "https://api.hh.ru/"
            assert api.timeout == 30
            assert api.max_retries == 3
            assert api.MAX_VACANCIES_PER_PAGE == 100
            assert api.MAX_PAGES == 20
            assert api.RATE_LIMIT_DELAY == 0.5

    def test_make_request_success(self, mock_session, mock_response):
        """Тест успешного выполнения запроса."""
        mock_response.json.return_value = {"test": "data"}
        mock_session.get.return_value = mock_response

        api = HH_API()
        result = api._make_request("https://api.hh.ru/test")

        assert result == {"test": "data"}
        mock_session.get.assert_called_once_with(
            "https://api.hh.ru/test",
            params=None,
            timeout=30
        )

    def test_make_request_400_error(self, mock_session):
        """Тест обработки ошибки 400."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            response=mock_response
        )
        mock_session.get.return_value = mock_response

        api = HH_API()
        result = api._make_request("https://api.hh.ru/test")

        assert result is None

    def test_make_request_429_error(self, mock_session):
        """Тест обработки ошибки 429 (Too Many Requests)."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            response=mock_response
        )
        mock_session.get.return_value = mock_response

        api = HH_API()
        api.max_retries = 2
        result = api._make_request("https://api.hh.ru/test")

        assert result is None
        assert mock_session.get.call_count == 2

    def test_get_company_success(self, mock_session, mock_response, sample_company_data):
        """Тест успешного получения компании."""
        mock_response.json.return_value = sample_company_data
        mock_session.get.return_value = mock_response

        api = HH_API()
        result = api.get_company(1740)

        assert result == sample_company_data
        mock_session.get.assert_called_once_with(
            "https://api.hh.ru/employers/1740",
            params=None,
            timeout=30
        )

    def test_get_company_invalid_id(self, mock_session):
        """Тест получения компании с некорректным ID."""
        api = HH_API()
        result = api.get_company(-1)

        assert result is None
        mock_session.get.assert_not_called()

    def test_search_companies(self, mock_session, mock_response):
        """Тест поиска компаний."""
        mock_response.json.return_value = {
            "items": [{"id": "1740", "name": "Яндекс"}],
            "found": 1
        }
        mock_session.get.return_value = mock_response

        api = HH_API()
        result = api.search_companies(text="яндекс", area=1)

        assert len(result) == 1
        assert result[0]["id"] == "1740"
        mock_session.get.assert_called_once_with(
            "https://api.hh.ru/employers",
            params={'text': 'яндекс', 'page': 0, 'per_page': 20, 'area': 1},
            timeout=30
        )

    def test_get_vacancies_success(self, mock_session, mock_response, sample_vacancies_list):
        """Тест успешного получения вакансий."""
        mock_response.json.return_value = {
            "items": sample_vacancies_list,
            "found": 2
        }
        mock_session.get.return_value = mock_response

        api = HH_API()
        result = api.get_vacancies(employer_id=1580604, page=1, per_page=50)

        assert len(result) == 2
        mock_session.get.assert_called_once_with(
            "https://api.hh.ru/vacancies",
            params={'employer_id': 1580604, 'page': 1, 'per_page': 50},
            timeout=30
        )

    def test_get_vacancies_max_page(self, mock_session):
        """Тест получения вакансий при превышении лимита страниц."""
        api = HH_API()
        result = api.get_vacancies(employer_id=1580604, page=20)

        assert result == []
        mock_session.get.assert_not_called()

    def test_get_all_company_vacancies_single_page(self, mock_session, mock_response):
        """Тест получения всех вакансий (одна страница)."""
        mock_response.json.return_value = {
            "items": [{"id": "1"}, {"id": "2"}],
            "found": 2
        }
        mock_session.get.return_value = mock_response

        api = HH_API()
        result = api.get_all_company_vacancies(1580604)

        assert len(result) == 2
        mock_session.get.assert_called_once()

    def test_get_all_company_vacancies_multiple_pages(self, mock_session):
        """Тест получения всех вакансий (несколько страниц)."""
        # Мокаем несколько страниц
        mock_response1 = MagicMock()
        mock_response1.json.return_value = {
            "items": [{"id": f"{i}"} for i in range(100)],
            "found": 250
        }
        mock_response1.status_code = 200

        mock_response2 = MagicMock()
        mock_response2.json.return_value = {
            "items": [{"id": f"{i}"} for i in range(100, 200)],
            "found": 250
        }
        mock_response2.status_code = 200

        mock_response3 = MagicMock()
        mock_response3.json.return_value = {
            "items": [{"id": f"{i}"} for i in range(200, 250)],
            "found": 250
        }
        mock_response3.status_code = 200

        mock_session.get.side_effect = [mock_response1, mock_response2, mock_response3]

        api = HH_API()
        api.MAX_VACANCIES_PER_PAGE = 100
        result = api.get_all_company_vacancies(1580604)

        assert len(result) == 250
        assert mock_session.get.call_count == 3

    def test_process_company_data(self, sample_company_data, sample_processed_company):
        """Тест обработки данных компании."""
        api = HH_API()
        result = api.process_company_data(sample_company_data)

        assert result is not None
        assert result['id'] == sample_processed_company['id']
        assert result['name'] == sample_processed_company['name']
        assert result['trusted'] == sample_processed_company['trusted']
        assert result['accredited_it_employer'] == sample_processed_company['accredited_it_employer']

    def test_process_company_data_empty(self):
        """Тест обработки пустых данных компании."""
        api = HH_API()
        result = api.process_company_data(None)
        assert result is None

    def test_process_vacancy_data_full(self, sample_vacancy_data, sample_processed_vacancy):
        """Тест обработки полных данных вакансии."""
        api = HH_API()
        result = api.process_vacancy_data(sample_vacancy_data)

        assert result is not None
        assert result['id'] == sample_processed_vacancy['id']
        assert result['name'] == sample_processed_vacancy['name']
        assert result['company_id'] == sample_processed_vacancy['company_id']
        assert result['salary_from'] == sample_processed_vacancy['salary_from']
        assert result['currency'] == sample_processed_vacancy['currency']
        assert result['area'] == sample_processed_vacancy['area']

    def test_process_vacancy_data_no_salary(self):
        """Тест обработки вакансии без зарплаты."""
        vacancy = {
            "id": "130548505",
            "name": "Личный водитель",
            "salary": None,
            "employer": {"id": "9197706"},
            "snippet": {},
            "published_at": "2026-02-18T07:55:48+0300"
        }

        api = HH_API()
        result = api.process_vacancy_data(vacancy)

        assert result['salary_from'] is None
        assert result['salary_to'] is None
        assert result['avg_salary'] is None

    def test_process_company_vacancies(self, mock_session, mock_response):
        """Тест обработки всех вакансий компании."""
        mock_response.json.return_value = {
            "items": [{"id": "1"}, {"id": "2"}],
            "found": 2
        }
        mock_session.get.return_value = mock_response

        with patch.object(HH_API, 'process_vacancy_data') as mock_process:
            mock_process.side_effect = [
                {"id": "1", "processed": True},
                {"id": "2", "processed": True}
            ]

            api = HH_API()
            result = api.process_company_vacancies(1580604)

            assert len(result) == 2
            assert mock_process.call_count == 2
