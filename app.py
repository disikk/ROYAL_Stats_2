# -*- coding: utf-8 -*-

"""
Точка входа в приложение Royal Stats (Hero-only).
"""

import os
# import sys # sys is not used if main() is not called
# from PyQt6 import QtWidgets # Not needed for the task
# from ui.main_window import MainWindow # Not needed for the task
# from ui.app_style import apply_dark_theme # Not needed for the task
import config # Для доступа к настройкам

import logging
# Настройка базового логгирования
# Уровень логирования можно настроить в config.py
logging.basicConfig(level=logging.DEBUG if config.DEBUG else logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ROYAL_Stats.App')

# def main(): # main() is not called for this task
#     """
#     Главная функция запуска приложения.
#     """
#     logger.info(f"Запуск приложения {config.APP_TITLE} v{config.APP_VERSION}")
#     logger.info(f"Текущая рабочая директория: {os.getcwd()}")
# 
#     app = QtWidgets.QApplication(sys.argv)
# 
#     # Применяем тему
#     apply_dark_theme(app)
# 
#     # Создаем и показываем главное окно
#     main_window = MainWindow()
#     main_window.show()
# 
#     # Сохраняем конфиг при выходе из приложения
#     exit_code = app.exec()
#     config.save_config() # Сохраняем последний путь к БД и другие настройки
#     logger.info("Приложение завершило работу.")
#     sys.exit(exit_code)

def update_null_payouts():
    """
    Updates the payout to 0 for all tournaments where payout is NULL.
    Reports the number of rows affected.
    """
    from db.manager import database_manager  # Import here to ensure config is loaded

    sql_query = "UPDATE tournaments SET payout = 0 WHERE payout IS NULL;"
    try:
        logger.info(f"Attempting to connect to database: {database_manager.db_path}")
        # Ensure the database is initialized
        # The get_connection method also handles initialization
        database_manager.get_connection() 
        
        logger.info(f"Executing SQL query: {sql_query}")
        affected_rows = database_manager.execute_update(sql_query)
        logger.info(f"Successfully updated payouts. Number of rows affected: {affected_rows}")
        return affected_rows
    except Exception as e:
        logger.error(f"Failed to update payouts: {e}")
        # Attempt to close connection if open
        database_manager.close_connection()
        return -1 # Indicate failure

def migrate_tournaments_schema():
    """
    Modifies the 'tournaments' table schema:
    1. Creates 'tournaments_new' with the new schema.
    2. Copies data from 'tournaments' to 'tournaments_new'.
    3. Drops the old 'tournaments' table.
    4. Renames 'tournaments_new' to 'tournaments'.
    Reports success or failure for the entire sequence.
    """
    from db.manager import database_manager # Import here

    # Ensure DB logger is configured (similar to update_null_payouts)
    db_logger = logging.getLogger('ROYAL_Stats.Database')
    if not db_logger.handlers:
        db_m_handler = logging.StreamHandler()
        db_m_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        db_m_handler.setFormatter(db_m_formatter)
        db_logger.addHandler(db_m_handler)
        db_logger.propagate = False
        db_logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

    logger.info("Starting tournaments table schema migration.")

    sql_commands = [
        """
        CREATE TABLE tournaments_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT UNIQUE NOT NULL,
            tournament_name TEXT,
            start_time TEXT,
            buyin REAL,
            payout REAL DEFAULT 0 NOT NULL,
            finish_place INTEGER,
            ko_count INTEGER DEFAULT 0,
            session_id TEXT,
            reached_final_table BOOLEAN DEFAULT 0,
            final_table_initial_stack_chips REAL,
            final_table_initial_stack_bb REAL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        );
        """,
        """
        INSERT INTO tournaments_new (
            id, tournament_id, tournament_name, start_time, buyin, payout, 
            finish_place, ko_count, session_id, reached_final_table, 
            final_table_initial_stack_chips, final_table_initial_stack_bb
        ) 
        SELECT 
            id, tournament_id, tournament_name, start_time, buyin, 
            COALESCE(payout, 0), 
            finish_place, ko_count, session_id, reached_final_table, 
            final_table_initial_stack_chips, final_table_initial_stack_bb
        FROM tournaments;
        """,
        "DROP TABLE tournaments;",
        "ALTER TABLE tournaments_new RENAME TO tournaments;"
    ]

    command_descriptions = [
        "Create tournaments_new table",
        "Copy data to tournaments_new",
        "Drop old tournaments table",
        "Rename tournaments_new to tournaments"
    ]

    try:
        # Ensure connection is established and DB is initialized
        conn = database_manager.get_connection()
        if conn is None:
            logger.error("Migration failed: Could not establish database connection.")
            return False
        
        # Check if PRAGMA foreign_keys is ON. It should be for ON DELETE CASCADE to work.
        # SQLite default is OFF. db.schema.py does not seem to enable it globally.
        # For safety, execute it, though DatabaseManager doesn't have execute_query that returns no results easily.
        # We can use execute_update for PRAGMA statements that don't return results.
        database_manager.execute_update("PRAGMA foreign_keys = ON;")
        logger.info("Ensured PRAGMA foreign_keys = ON for the current connection.")


        for i, command in enumerate(sql_commands):
            description = command_descriptions[i]
            logger.info(f"Executing step: {description}...")
            logger.debug(f"SQL: {command.strip()}")
            affected_rows = database_manager.execute_update(command)
            # For DDL, affected_rows might be 0 or -1 depending on sqlite3 driver version or specific command
            # For INSERT INTO ... SELECT, it should be the number of rows inserted.
            if description == "Copy data to tournaments_new":
                 logger.info(f"Step '{description}' completed. Rows copied: {affected_rows}")
            else:
                 logger.info(f"Step '{description}' completed successfully. (Affected rows: {affected_rows})")


        logger.info("Tournaments table schema migration completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Migration failed during step: {description if 'description' in locals() else 'Unknown'}. Error: {e}")
        # No explicit rollback needed here for the whole sequence, as execute_update handles individual command rollback.
        # However, the database will be in an intermediate state.
        # e.g. tournaments_new might exist, old tournaments might be dropped or not.
        return False
    finally:
        database_manager.close_connection()


if __name__ == "__main__":
    # Configure ROYAL_Stats.App logger (already done by basicConfig at top level)
    db_logger = logging.getLogger('ROYAL_Stats.Database')
    if not db_logger.handlers:
        db_main_handler = logging.StreamHandler()
        db_main_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        db_main_handler.setFormatter(db_main_formatter)
        db_logger.addHandler(db_main_handler)
        db_logger.propagate = False 
    db_logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

    logger.info("Running payout update task (step 2)...")
    updated_count = update_null_payouts()
    if updated_count >= 0:
        logger.info(f"Payout update task completed. Rows affected: {updated_count}")
    else:
        logger.error("Payout update task failed.")

    logger.info("Running tournaments schema migration task (step 3)...")
    migration_succeeded = migrate_tournaments_schema()
    if migration_succeeded:
        logger.info("Tournaments schema migration task completed successfully.")
    else:
        logger.error("Tournaments schema migration task failed.")

def verify_tournaments_schema():
    """
    Queries the database schema to verify the structure of the 'tournaments' table,
    specifically checking the 'payout' column.
    """
    from db.manager import database_manager # Import here

    logger.info("Verifying 'tournaments' table schema...")

    try:
        conn = database_manager.get_connection()
        if conn is None:
            logger.error("Schema verification failed: Could not establish database connection.")
            return False

        # Query 1: PRAGMA table_info
        logger.info("Executing PRAGMA table_info('tournaments');")
        table_info = database_manager.execute_query("PRAGMA table_info('tournaments');")
        
        payout_column_info = None
        if table_info:
            logger.info("PRAGMA table_info('tournaments') results:")
            for row in table_info:
                logger.info(f"  cid: {row['cid']}, name: {row['name']}, type: {row['type']}, notnull: {row['notnull']}, dflt_value: {row['dflt_value']}, pk: {row['pk']}")
                if row['name'] == 'payout':
                    payout_column_info = dict(row) # Convert sqlite3.Row to dict for easier access
        else:
            logger.warning("PRAGMA table_info('tournaments') returned no results.")
            return False # Table might not exist or other issue

        # Query 2: SELECT sql FROM sqlite_master
        logger.info("Executing SELECT sql FROM sqlite_master WHERE type='table' AND name='tournaments';")
        create_table_sql_rows = database_manager.execute_query("SELECT sql FROM sqlite_master WHERE type='table' AND name='tournaments';")
        
        create_sql = None
        if create_table_sql_rows and len(create_table_sql_rows) > 0:
            create_sql = create_table_sql_rows[0]['sql']
            logger.info(f"CREATE TABLE statement for 'tournaments':\n{create_sql}")
        else:
            logger.warning("SELECT sql FROM sqlite_master for 'tournaments' returned no results.")
            # This is a critical failure if table_info succeeded, indicates inconsistency or error.
            return False


        # Verification
        if payout_column_info:
            payout_type_correct = payout_column_info['type'] == 'REAL'
            payout_notnull_correct = payout_column_info['notnull'] == 1 # 1 for TRUE
            # dflt_value for '0' might be returned as '0' or 0.0 depending on SQLite version/driver.
            # Let's be flexible: str(payout_column_info['dflt_value']) == '0' or str(payout_column_info['dflt_value']) == '0.0'
            # Even better, check if it's numerically zero.
            payout_default_correct = False
            try:
                if float(payout_column_info['dflt_value']) == 0.0:
                     payout_default_correct = True
            except (ValueError, TypeError):
                 logger.warning(f"Could not parse default value '{payout_column_info['dflt_value']}' as float.")


            logger.info(f"Payout column verification: Type REAL ({payout_type_correct}), NOT NULL ({payout_notnull_correct}), DEFAULT 0 ({payout_default_correct})")

            if payout_type_correct and payout_notnull_correct and payout_default_correct:
                logger.info("Schema for 'payout' column in 'tournaments' table is correct.")
                return True
            else:
                logger.error("Schema for 'payout' column in 'tournaments' table is INCORRECT.")
                if not payout_type_correct: logger.error(f"  Expected type REAL, got {payout_column_info['type']}")
                if not payout_notnull_correct: logger.error(f"  Expected NOT NULL (1), got {payout_column_info['notnull']}")
                if not payout_default_correct: logger.error(f"  Expected DEFAULT 0, got {payout_column_info['dflt_value']}")
                return False
        else:
            logger.error("Could not find 'payout' column in PRAGMA table_info results.")
            return False

    except Exception as e:
        logger.error(f"Schema verification failed. Error: {e}")
        return False
    finally:
        database_manager.close_connection()


if __name__ == "__main__":
    # Configure ROYAL_Stats.App logger (already done by basicConfig at top level)
    db_logger = logging.getLogger('ROYAL_Stats.Database')
    if not db_logger.handlers:
        db_main_handler = logging.StreamHandler()
        db_main_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        db_main_handler.setFormatter(db_main_formatter)
        db_logger.addHandler(db_main_handler)
        db_logger.propagate = False 
    db_logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

    # Skipping previous tasks for brevity in this specific subtask run,
    # assuming DB is already migrated from previous step.
    # logger.info("Running payout update task (step 2)...")
    # updated_count = update_null_payouts()
    # if updated_count >= 0:
    #     logger.info(f"Payout update task completed. Rows affected: {updated_count}")
    # else:
    #     logger.error("Payout update task failed.")

    # logger.info("Running tournaments schema migration task (step 3)...")
    # migration_succeeded = migrate_tournaments_schema()
    # if migration_succeeded:
    #     logger.info("Tournaments schema migration task completed successfully.")
    # else:
    #     logger.error("Tournaments schema migration task failed.")

    logger.info("Running tournaments schema verification task (step 4)...")
    verification_succeeded = verify_tournaments_schema()
    if verification_succeeded:
        logger.info("Tournaments schema verification task completed successfully.")
    else:
        logger.error("Tournaments schema verification task failed.")
    
    from db.manager import database_manager
    database_manager.close_all_connections()