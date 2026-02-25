"""
Главный модуль программы для сбора и анализа вакансий с hh.ru.
Добавлена возможность загрузки свежих данных из главного меню.
"""

import sys
from pathlib import Path
import time

sys.path.append(str(Path(__file__).parent))

from src.api.hh_api import HH_API
from src.db.db_creator import DBCreator
from src.db.database_manager import DBManager
from src.utils.config import Config
from src.utils.validators import DataValidator


def check_postgres_version():
    """Проверка версии PostgreSQL."""
    try:
        import subprocess
        result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ PostgreSQL: {version}")

            import re
            match = re.search(r'(\d+\.\d+)', version)
            if match:
                version_num = float(match.group(1))
                if version_num < 9.6:
                    print("⚠️  Версия PostgreSQL ниже 9.6. Некоторые функции могут не работать")
            return True
    except FileNotFoundError:
        print("⚠️  PostgreSQL не найден в PATH")
    except Exception as e:
        print(f"⚠️  Не удалось проверить версию PostgreSQL: {e}")

    return False


def print_section(title: str):
    """Вывод секции с заголовком."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def format_salary(vacancy: dict) -> str:
    """
    Форматирование зарплаты для красивого вывода.

    Args:
        vacancy (dict): Данные вакансии

    Returns:
        str: Отформатированная строка с зарплатой
    """
    salary_parts = []
    currency = vacancy.get('currency', '')
    currency_display = f" {currency}" if currency else " руб."

    if vacancy.get('salary_from') and vacancy.get('salary_to'):
        salary_parts.append(f"от {vacancy['salary_from']:,.0f} до {vacancy['salary_to']:,.0f}".replace(',', ' '))
    elif vacancy.get('salary_from'):
        salary_parts.append(f"от {vacancy['salary_from']:,.0f}".replace(',', ' '))
    elif vacancy.get('salary_to'):
        salary_parts.append(f"до {vacancy['salary_to']:,.0f}".replace(',', ' '))
    else:
        return "не указана"

    return " ".join(salary_parts) + currency_display


def format_avg_salary(vacancy: dict) -> str:
    """
    Форматирование средней зарплаты.

    Args:
        vacancy (dict): Данные вакансии

    Returns:
        str: Отформатированная строка со средней зарплатой
    """
    if not vacancy.get('avg_salary'):
        return "не указана"

    currency = vacancy.get('currency', '')
    currency_display = f" {currency}" if currency else " руб."

    return f"{vacancy['avg_salary']:,.0f}{currency_display}".replace(',', ' ')


def print_vacancy(vacancy: dict, index: int = None):
    """
    Красивый вывод информации о вакансии.

    Args:
        vacancy (dict): Данные вакансии
        index (int, optional): Номер вакансии
    """
    if not vacancy:
        return

    prefix = f"{index}. " if index else ""
    print(f"{prefix}📌 {vacancy.get('vacancy_name', 'Без названия')}")
    print(f"   Компания: {vacancy.get('company_name', 'Не указана')}")
    print(f"   Зарплата: {format_salary(vacancy)}")
    print(f"   Средняя: {format_avg_salary(vacancy)}")

    if vacancy.get('area'):
        print(f"   Регион: {vacancy['area']}")

    if vacancy.get('experience'):
        print(f"   Опыт: {vacancy['experience']}")

    if vacancy.get('employment'):
        print(f"   Занятость: {vacancy['employment']}")

    print(f"   Ссылка: {vacancy.get('url', 'Не указана')}")
    print()


def print_company_stats(company: dict):
    """
    Вывод статистики по компании.

    Args:
        company (dict): Данные компании
    """
    if not company:
        return

    print(f"🏢 {company['company_name']}")
    print(f"   Вакансий в БД: {company['vacancies_count']}")
    print(f"   Открыто вакансий (hh.ru): {company['hh_vacancies_count']}")
    if company.get('trusted'):
        print("   ✅ Проверенная компания")
    if company.get('accredited_it_employer'):
        print("   💻 Аккредитованная IT-компания")
    print()


def setup_database():
    """
    Настройка базы данных: создание БД и таблиц.
    """
    print_section("НАСТРОЙКА БАЗЫ ДАННЫХ")

    config = Config()

    # Проверка конфигурации
    config_checks = config.validate_config()
    print("📋 Проверка конфигурации:")
    for check, status in config_checks.items():
        status_symbol = "✅" if status else "❌"
        print(f"   {status_symbol} {check}")

    if not all(config_checks.values()):
        print("\n⚠️  Обнаружены проблемы в конфигурации:")
        if not config_checks['db_host']:
            print("   - Не указан хост БД")
        if not config_checks['db_port']:
            print("   - Некорректный порт БД")
        if not config_checks['db_name']:
            print("   - Не указано имя БД")
        if not config_checks['db_user']:
            print("   - Не указан пользователь БД")

        response = input("\nПродолжить с текущей конфигурацией? (y/n): ").strip().lower()
        if response != 'y':
            print("❌ Программа завершена")
            return False

    db_creator = DBCreator(config.get_db_connection_params())

    print("\n📦 Создание базы данных...")
    if not db_creator.create_database():
        print("❌ Не удалось создать базу данных.")
        return False

    print("📦 Создание таблиц...")
    if not db_creator.create_tables():
        print("❌ Не удалось создать таблицы.")
        return False

    print("✅ База данных успешно настроена")
    return True


def load_data_to_db(show_progress: bool = True) -> bool:
    """
    Загрузка данных о компаниях и вакансиях в БД.

    Args:
        show_progress (bool): Показывать ли прогресс загрузки

    Returns:
        bool: True если загрузка успешна
    """
    if show_progress:
        print_section("ЗАГРУЗКА ДАННЫХ В БАЗУ ДАННЫХ")

    config = Config()
    companies = config.load_companies()

    if not companies:
        print("❌ Список компаний пуст!")
        return False

    if show_progress:
        print(f"📊 Найдено компаний для обработки: {len(companies)}")
        print("Список компаний:")
        for i, company_id in enumerate(companies[:10], 1):
            print(f"   {i}. ID: {company_id}")

    hh_api = HH_API(config)
    total_vacancies = 0
    total_errors = 0
    start_time = time.time()

    with DBManager(config.get_db_connection_params()) as db_manager:
        # Проверка подключения к БД
        if not db_manager.test_connection():
            print("❌ Не удалось подключиться к БД")
            return False

        for i, company_id in enumerate(companies, 1):
            if show_progress:
                print(f"\n[{i}/{len(companies)}] Обработка компании ID: {company_id}")

            # Валидация ID компании
            valid_id = DataValidator.validate_company_id(company_id)
            if not valid_id:
                if show_progress:
                    print(f"  ⚠️  Некорректный ID компании: {company_id}")
                total_errors += 1
                continue

            # Получаем данные компании
            company_data = hh_api.get_company(valid_id)
            if not company_data:
                if show_progress:
                    print(f"  ⚠️  Не удалось получить данные о компании {valid_id}")
                total_errors += 1
                continue

            processed_company = hh_api.process_company_data(company_data)
            if not processed_company:
                if show_progress:
                    print(f"  ⚠️  Не удалось обработать данные компании {valid_id}")
                total_errors += 1
                continue

            success, error = db_manager.insert_company(processed_company)
            if success:
                if show_progress:
                    print(f"  ✅ Компания '{processed_company['name']}' сохранена")
            else:
                if show_progress:
                    print(f"  ⚠️  {error}")
                total_errors += 1
                continue

            # Получаем и сохраняем вакансии
            vacancies = hh_api.process_company_vacancies(valid_id)

            if vacancies:
                count, errors = db_manager.insert_vacancies_batch(vacancies)
                total_vacancies += count
                total_errors += len(errors)
                if show_progress:
                    print(f"  ✅ Сохранено вакансий: {count}")
                    if errors:
                        print(f"  ⚠️  Ошибок при сохранении: {len(errors)}")
            else:
                if show_progress:
                    print("  ℹ️  Вакансий не найдено")

            # Небольшая задержка между компаниями
            time.sleep(1)

    elapsed_time = time.time() - start_time
    if show_progress:
        print(f"\n📊 Итоги загрузки:")
        print(f"   ✅ Успешно загружено вакансий: {total_vacancies}")
        print(f"   ⚠️  Ошибок: {total_errors}")
        print(f"   ⏱  Время выполнения: {elapsed_time:.2f} сек")
    else:
        print(f"✅ Загружено {total_vacancies} вакансий за {elapsed_time:.2f} сек")

    return total_vacancies > 0


def database_management_menu():
    """
    Меню управления базой данных.
    """
    config = Config()
    db_creator = DBCreator(config.get_db_connection_params())

    while True:
        print_section("УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ")

        # Показываем информацию о текущей БД
        db_info = db_creator.get_database_info()
        print(f"📊 Текущая база данных: {db_info['name']}")
        print(f"   Существует: {'✅ Да' if db_info['exists'] else '❌ Нет'}")
        if db_info['exists']:
            print(f"   Размер: {db_info['size']}")
            print(f"   Таблиц: {db_info['tables_count']}")
            print(f"   Активных подключений: {db_info['active_connections']}")

        print("\n🔧 Доступные действия:")
        print("1. 🗑️  Удалить базу данных полностью")
        print("2. 🔄 Пересоздать базу данных (удалить и создать заново)")
        print("3. 🧹 Очистить все таблицы (удалить данные, оставить структуру)")
        print("4. 📋 Показать информацию о БД")
        print("5. 📥 Загрузить свежие данные после удаления")  # Новый пункт
        print("0. ↩️  Вернуться в главное меню")

        choice = input("\nВыберите действие (0-5): ").strip()

        if choice == '0':
            break

        elif choice == '1':
            print_section("УДАЛЕНИЕ БАЗЫ ДАННЫХ")
            print(f"⚠️  ВНИМАНИЕ! Вы собираетесь удалить базу данных {db_info['name']}")
            print("   Все данные будут безвозвратно потеряны!")

            confirm = input("\nДля подтверждения введите название базы данных: ").strip()
            if confirm == db_info['name']:
                success, message = db_creator.drop_database(force=True)
                print(message)

                # Предложение загрузить данные после удаления
                if success:
                    response = input("\nХотите загрузить свежие данные в новую базу? (y/n): ").strip().lower()
                    if response == 'y':
                        # Создаем БД заново
                        if db_creator.create_database() and db_creator.create_tables():
                            print("✅ База данных создана, начинаем загрузку...")
                            load_data_to_db()
                        else:
                            print("❌ Не удалось создать базу данных")
            else:
                print("❌ Название БД не совпадает. Операция отменена.")

        elif choice == '2':
            print_section("ПЕРЕСОЗДАНИЕ БАЗЫ ДАННЫХ")
            success, message = db_creator.recreate_database()
            print(message)

            # Предложение загрузить данные после пересоздания
            if success:
                response = input("\nХотите загрузить свежие данные? (y/n): ").strip().lower()
                if response == 'y':
                    load_data_to_db()

        elif choice == '3':
            print_section("ОЧИСТКА ТАБЛИЦ")
            print("⚠️  Все данные в таблицах будут удалены!")
            print("   Структура таблиц сохранится.")

            response = input("\nПродолжить? (y/n): ").strip().lower()
            if response == 'y':
                if db_creator.clear_tables():
                    print("✅ Таблицы успешно очищены")

                    # Предложение загрузить данные после очистки
                    response = input("\nХотите загрузить свежие данные? (y/n): ").strip().lower()
                    if response == 'y':
                        load_data_to_db()
                else:
                    print("❌ Ошибка при очистке таблиц")

        elif choice == '4':
            print_section("ИНФОРМАЦИЯ О БАЗЕ ДАННЫХ")
            db_info = db_creator.get_database_info()
            print(f"📌 Имя БД: {db_info['name']}")
            print(f"📌 Существует: {'Да' if db_info['exists'] else 'Нет'}")
            if db_info['exists']:
                print(f"📌 Размер: {db_info['size']}")
                print(f"📌 Количество таблиц: {db_info['tables_count']}")
                print(f"📌 Активные подключения: {db_info['active_connections']}")

                # Показываем список таблиц
                try:
                    with DBManager(config.get_db_connection_params()) as db_manager:
                        query = """
                            SELECT table_name, 
                                   (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as columns_count
                            FROM information_schema.tables t
                            WHERE table_schema = 'public'
                            ORDER BY table_name
                        """
                        tables = db_manager.execute_query(query)
                        if tables:
                            print("\n📋 Таблицы:")
                            for table in tables:
                                print(f"   - {table['table_name']} ({table['columns_count']} колонок)")
                except Exception as e:
                    print(f"   ⚠️  Не удалось получить список таблиц: {e}")
            else:
                print("\n💡 База данных не существует. Создайте её через настройку.")

        elif choice == '5':
            print_section("ЗАГРУЗКА СВЕЖИХ ДАННЫХ")

            # Проверяем существование БД
            if not db_info['exists']:
                print("❌ База данных не существует. Сначала создайте её.")
                response = input("\nСоздать базу данных? (y/n): ").strip().lower()
                if response == 'y':
                    if db_creator.create_database() and db_creator.create_tables():
                        print("✅ База данных создана")
                        load_data_to_db()
                continue

            # Проверяем наличие таблиц
            if db_info['tables_count'] < 2:
                print("⚠️  Таблицы не найдены. Создаём таблицы...")
                if not db_creator.create_tables():
                    print("❌ Не удалось создать таблицы")
                    continue

            # Спрашиваем, очистить ли данные перед загрузкой
            if db_info['tables_count'] > 0:
                response = input("\nОчистить существующие данные перед загрузкой? (y/n): ").strip().lower()
                if response == 'y':
                    if db_creator.clear_tables():
                        print("✅ Данные очищены")
                    else:
                        print("⚠️  Не удалось очистить данные, но продолжим загрузку")

            # Загружаем данные
            load_data_to_db()

        else:
            print("❌ Неверный выбор")

        input("\nНажмите Enter для продолжения...")


def user_interaction():
    """
    Функция взаимодействия с пользователем.
    """
    config = Config()

    while True:
        print_section("ГЛАВНОЕ МЕНЮ")
        print("1. 📊 Показать все компании и количество вакансий")
        print("2. 📋 Показать все вакансии")
        print("3. 💰 Показать среднюю зарплату по всем вакансиям")
        print("4. ⬆️  Показать вакансии с зарплатой выше средней")
        print("5. 🔍 Поиск вакансий по ключевому слову")
        print("6. 🌍 Показать вакансии по региону")
        print("7. 📈 Показать статистику по компаниям")
        print("8. 📊 Показать общую статистику БД")
        print("9. 🔧 Управление базой данных")
        print("10. 📥 Загрузить свежие данные")  # НОВЫЙ ПУНКТ
        print("0. 🚪 Выход")

        choice = input("\nВыберите действие (0-10): ").strip()

        if choice == '0':
            print("\n👋 До свидания!")
            break

        # Новый пункт 10 - загрузка свежих данных
        elif choice == '10':
            load_data_to_db()
            continue

        elif choice == '9':
            database_management_menu()
            continue

        try:
            with DBManager(config.get_db_connection_params()) as db_manager:

                # Проверка подключения
                if not db_manager.test_connection():
                    print("❌ Ошибка подключения к БД")
                    continue

                if choice == '1':
                    print_section("КОМПАНИИ И КОЛИЧЕСТВО ВАКАНСИЙ")
                    companies = db_manager.get_companies_and_vacancies_count()

                    if not companies:
                        print("❌ Нет данных о компаниях.")
                        continue

                    for company in companies:
                        print_company_stats(company)

                elif choice == '2':
                    print_section("ВСЕ ВАКАНСИИ")
                    vacancies = db_manager.get_all_vacancies(limit=50)

                    if not vacancies:
                        print("❌ Нет данных о вакансиях.")
                        continue

                    print(f"📊 Найдено вакансий: {len(vacancies)}\n")
                    for i, vacancy in enumerate(vacancies[:20], 1):
                        print_vacancy(vacancy, i)

                    if len(vacancies) > 20:
                        print(f"... и еще {len(vacancies) - 20} вакансий")

                elif choice == '3':
                    print_section("СРЕДНЯЯ ЗАРПЛАТА")
                    avg_salary = db_manager.get_avg_salary()

                    if avg_salary:
                        print(f"💰 Средняя зарплата по всем вакансиям: {avg_salary:,.0f} руб.".replace(',', ' '))
                    else:
                        print("❌ Нет данных для расчета средней зарплаты.")

                elif choice == '4':
                    print_section("ВАКАНСИИ С ЗАРПЛАТОЙ ВЫШЕ СРЕДНЕЙ")
                    vacancies = db_manager.get_vacancies_with_higher_salary()

                    if not vacancies:
                        print("❌ Нет вакансий с зарплатой выше средней.")
                        continue

                    avg_salary = db_manager.get_avg_salary()
                    print(f"📊 Средняя зарплата: {avg_salary:,.0f} руб.".replace(',', ' '))
                    print(f"📊 Найдено вакансий: {len(vacancies)}\n")

                    for i, vacancy in enumerate(vacancies[:15], 1):
                        print_vacancy(vacancy, i)

                    if len(vacancies) > 15:
                        print(f"... и еще {len(vacancies) - 15} вакансий")

                elif choice == '5':
                    print_section("ПОИСК ВАКАНСИЙ ПО КЛЮЧЕВОМУ СЛОВУ")
                    keyword = input("Введите ключевое слово для поиска (минимум 2 символа): ").strip()

                    if not keyword or len(keyword) < 2:
                        print("❌ Ключевое слово должно содержать минимум 2 символа.")
                        continue

                    vacancies = db_manager.get_vacancies_with_keyword(keyword)

                    if not vacancies:
                        print(f"❌ Вакансий, содержащих '{keyword}', не найдено.")
                        continue

                    print(f"\n📊 Найдено вакансий: {len(vacancies)}\n")
                    for i, vacancy in enumerate(vacancies[:15], 1):
                        print_vacancy(vacancy, i)

                    if len(vacancies) > 15:
                        print(f"... и еще {len(vacancies) - 15} вакансий")

                elif choice == '6':
                    print_section("ПОИСК ВАКАНСИЙ ПО РЕГИОНУ")
                    area = input("Введите название региона (минимум 2 символа): ").strip()

                    if not area or len(area) < 2:
                        print("❌ Название региона должно содержать минимум 2 символа.")
                        continue

                    vacancies = db_manager.get_vacancies_by_area(area)

                    if not vacancies:
                        print(f"❌ Вакансий в регионе '{area}' не найдено.")
                        continue

                    print(f"\n📊 Найдено вакансий в регионе '{area}': {len(vacancies)}\n")
                    for i, vacancy in enumerate(vacancies[:15], 1):
                        print_vacancy(vacancy, i)

                    if len(vacancies) > 15:
                        print(f"... и еще {len(vacancies) - 15} вакансий")

                elif choice == '7':
                    print_section("СТАТИСТИКА ПО КОМПАНИЯМ")
                    stats = db_manager.get_companies_stats()

                    if not stats:
                        print("❌ Нет данных для статистики.")
                        continue

                    for stat in stats:
                        print(f"🏢 {stat['company_name']}")
                        print(f"   Всего вакансий: {stat['total_vacancies']}")
                        if stat['avg_salary']:
                            print(f"   Средняя зарплата: {stat['avg_salary']:,.0f} руб.".replace(',', ' '))
                        if stat['min_salary'] or stat['max_salary']:
                            print(f"   Диапазон зарплат: {stat['min_salary'] or 'не указано'} - {stat['max_salary'] or 'не указано'}")
                        print(f"   Регионов: {stat['regions_count']}")
                        print()

                elif choice == '8':
                    print_section("ОБЩАЯ СТАТИСТИКА БД")
                    stats = db_manager.get_database_stats()

                    if stats:
                        print(f"📊 Всего компаний: {stats.get('total_companies', 0)}")
                        print(f"📊 Всего вакансий: {stats.get('total_vacancies', 0)}")
                        print(f"🌍 Регионов: {stats.get('total_areas', 0)}")
                        print(f"💰 Средняя зарплата: {stats.get('overall_avg_salary', 0):,.0f} руб.".replace(',', ' '))
                        print(f"📉 Минимальная средняя: {stats.get('min_avg_salary', 0):,.0f} руб.".replace(',', ' '))
                        print(f"📈 Максимальная средняя: {stats.get('max_avg_salary', 0):,.0f} руб.".replace(',', ' '))
                    else:
                        print("❌ Нет данных для статистики.")

                else:
                    print("❌ Неверный выбор. Пожалуйста, выберите действие от 0 до 10.")

        except Exception as e:
            print(f"❌ Произошла ошибка: {e}")
            print("Пожалуйста, проверьте подключение к БД и повторите попытку.")

        input("\nНажмите Enter для продолжения...")


def main():
    """
    Главная функция программы.
    """
    print("=" * 70)
    print("       ПАРСЕР ВАКАНСИЙ С hh.ru v2.0")
    print("=" * 70)

    # Проверка версии PostgreSQL
    check_postgres_version()

    # Проверка наличия .env файла
    env_path = Path(__file__).parent / '.env'
    if not env_path.exists():
        print("\n⚠️  Файл .env не найден!")
        print("Создайте файл .env на основе .env.example и укажите свои настройки БД")

        response = input("\nПродолжить с настройками по умолчанию? (y/n): ").strip().lower()
        if response != 'y':
            print("❌ Программа завершена")
            return

    # Настройка базы данных
    if not setup_database():
        return

    print("\nХотите загрузить свежие данные о вакансиях?")
    response = input("(y/n): ").strip().lower()

    if response == 'y':
        if load_data_to_db():
            print("\n✅ Данные успешно загружены в базу данных!")
        else:
            print("\n⚠️  Не удалось загрузить данные. Проверьте логи выше.")
    else:
        print("\n⚠️  Используем существующие данные в базе.")

    user_interaction()


if __name__ == "__main__":
    main()
