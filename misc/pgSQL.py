import json
from config import connection_pool, logger


# Подключение к БД (инициализация пула)
def pgConnect():
    try:
        # Пул уже инициализирован в config.py, проверяем наличие соединений
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                logger.info("Database connection is OK")
                conn.commit()
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Error connection to database: {e}")


# Проверка существования пользователя
def check_user(tg_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM Users WHERE tg_id = %s", (tg_id,))
                return cur.fetchone() is not None
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка проверки пользователя (check_user): \n{e}")
        return False


# Добавление нового пользователя
def add_user(tg_id, age, gender):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute('''INSERT INTO Users (tg_id, age, gender) 
                              VALUES (%s, %s, %s) 
                              ON CONFLICT (tg_id) DO NOTHING''', (tg_id, age, gender))
                conn.commit()
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка добавления пользователя (add_user): \n{e}")


# Функция для получения списка непройденных опросов из БД
def get_new_surveys(user_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT s.id, s.name 
                    FROM surveys s
                    WHERE s.id NOT IN (
                        SELECT survey_id 
                        FROM current_users_questions 
                        WHERE user_id = %s
                    )
                    ORDER BY s.id
                """
                cur.execute(query, (user_id,))
                rows = cur.fetchall()
                return [(row[1], row[0]) for row in rows]  # (name, ID_Opinion)
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка получения непройденных опросов (get_new_surveys): \n{e}")
        return []


# Функция для получения списка незавершенных опросов из БД
def get_uncompleted_surveys(user_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT s.id, s.name 
                    FROM surveys s
                    JOIN current_users_questions cuq ON s.id = cuq.survey_id
                    WHERE cuq.user_id = %s AND cuq.is_completed_survey = false
                    GROUP BY s.id, s.name
                    ORDER BY s.id
                """
                cur.execute(query, (user_id,))
                rows = cur.fetchall()
                return [(row[1], row[0]) for row in rows]  # (name, ID_Opinion)
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка получения незавершенных опросов (get_uncompleted_surveys): \n{e}")
        return []


# Функция для получения вопросов по ID опроса
def get_questions(opinion_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id, question FROM questions WHERE survey_id = %s', (opinion_id,))
                rows = cur.fetchall()
                # Преобразуем в список JSON-объектов с id и question
                result = [{"id": row[0], "question": row[1]} for row in rows]
                return json.dumps(result, ensure_ascii=False)
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка get_questions получения вопросов (get_questions): \n{e}")
        return json.dumps([])


# Функция для сохранения ответа и обновления текущего вопроса
def SaveAns_UpdateQuest(tg_id, opinion_id, question_id, answer, next_question_id=None):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Сохраняем ответ в UsersAnswers, если ответ предоставлен
                if answer is not None:
                    answer_json = json.dumps({"answer": answer}, ensure_ascii=False)
                    cur.execute('''INSERT INTO users_answers (quest_id, survey_id, user_id, answer)
                                 VALUES (%s, %s, %s, %s)''',
                               (question_id, opinion_id, tg_id, answer_json))
                
                # Удаляем существующую запись для этого пользователя и опроса
                cur.execute('''DELETE FROM current_users_questions 
                              WHERE user_id = %s AND survey_id = %s''', (tg_id, opinion_id))
                
                # Вставляем новую запись
                is_completed = next_question_id is None
                cur.execute('''INSERT INTO current_users_questions (survey_id, quest_id, user_id, "is_completed_survey")
                             VALUES (%s, %s, %s, %s)''',
                           (opinion_id, next_question_id if next_question_id else question_id, tg_id, is_completed))
                
                conn.commit()
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка при сохранении ответа/обновлении вопроса (SaveAns_UpdateQuest): \n{e}")



# Функция для установки статуса паузы опроса в базе данных
def set_survey_paused(user_id, opinion_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''UPDATE current_users_questions 
                       SET "is_completed_survey" = %s 
                       WHERE user_id = %s AND survey_id = %s''',
                    (False, user_id, opinion_id)
                )
                conn.commit()
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка при установке статуса паузы (set_survey_paused): \n{e}")

# Функция для получения текущего вопроса из базы данных
def get_current_question_id(user_id, opinion_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''SELECT quest_id 
                       FROM current_users_questions 
                       WHERE user_id = %s AND survey_id = %s''',
                    (user_id, opinion_id)
                )
                result = cur.fetchone()
                return result[0] if result else None
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка получения текущего вопроса (get_current_question_id): \n{e}")
        return None