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


# Проверка существования респондента в таблице respondents
def check_user(tg_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM respondents WHERE id = %s", (tg_id,))
                return cur.fetchone() is not None
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка проверки респондента (check_user): \n{e}")
        return False



# Добавление нового респондента в таблицу respondents
def add_user(tg_id, age, gender):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute('''INSERT INTO respondents (id, age, gender) 
                               VALUES (%s, %s, %s) 
                               ON CONFLICT (id) DO NOTHING''', 
                            (tg_id, age, gender))
                conn.commit()
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка добавления респондента (add_user): \n{e}")


# Получение списка опросов, которые пользователь ещё не проходил
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
                        FROM survey_responses
                        WHERE respondent_id = %s
                    )
                    ORDER BY s.id
                """
                cur.execute(query, (user_id,))
                rows = cur.fetchall()
                return [(row[1], row[0]) for row in rows]
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка получения новых опросов (get_new_surveys): \n{e}")
        return []



# Получение списка опросов, которые пользователь начал, но не завершил
def get_uncompleted_surveys(user_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT s.id, s.name
                    FROM surveys s
                    JOIN survey_responses sr ON s.id = sr.survey_id
                    WHERE sr.respondent_id = %s
                      AND sr.submitted_at IS NULL
                    ORDER BY s.id
                """
                cur.execute(query, (user_id,))
                rows = cur.fetchall()
                return [(row[1], row[0]) for row in rows]
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка получения незавершённых опросов (get_uncompleted_surveys): \n{e}")
        return []
    

# Получение всех вопросов и их вариантов для указанного опроса
def get_questions(survey_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Получаем вопросы
                cur.execute("""
                    SELECT q.id, q.type, q.question_text, q.max_choices
                    FROM questions q
                    WHERE q.survey_id = %s
                    ORDER BY q.position
                """, (survey_id,))
                questions = cur.fetchall()

                result = []
                for q_id, q_type, q_text, max_choices in questions:
                    cur.execute("""
                        SELECT option_text
                        FROM question_options
                        WHERE question_id = %s
                        ORDER BY position
                    """, (q_id,))
                    options = [r[0] for r in cur.fetchall()]
                    result.append({
                        "id": q_id,
                        "type": q_type,
                        "question_text": q_text,
                        "options": options,
                        "max_choices": max_choices
                    })
                return json.dumps(result, ensure_ascii=False)
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка получения вопросов (get_questions): \n{e}")
        return json.dumps([])



# Сохранение ответа и обновление текущего состояния (survey_responses)
def SaveAns_UpdateQuest(tg_id, survey_id, question_id, answer, next_question_id=None):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Получаем или создаём запись прохождения опроса
                cur.execute("""
                    SELECT id FROM survey_responses
                    WHERE survey_id = %s AND respondent_id = %s AND submitted_at IS NULL
                """, (survey_id, tg_id))
                response = cur.fetchone()
                if response:
                    response_id = response[0]
                else:
                    cur.execute("""
                        INSERT INTO survey_responses (survey_id, respondent_id)
                        VALUES (%s, %s)
                        RETURNING id
                    """, (survey_id, tg_id))
                    response_id = cur.fetchone()[0]

                # Сохраняем ответ, если он есть
                if answer is not None:
                    cur.execute("SELECT type FROM questions WHERE id = %s", (question_id,))
                    q_type = cur.fetchone()[0]

                    if q_type == "text":
                        cur.execute("""
                            INSERT INTO answers (response_id, question_id, answer_text)
                            VALUES (%s, %s, %s)
                        """, (response_id, question_id, str(answer)))

                    elif q_type == "scale":
                        cur.execute("""
                            INSERT INTO answers (response_id, question_id, answer_number)
                            VALUES (%s, %s, %s)
                        """, (response_id, question_id, int(answer)))

                    elif q_type == "single_choice":
                        cur.execute("""
                            SELECT id FROM question_options
                            WHERE question_id = %s AND option_text = %s
                        """, (question_id, str(answer)))
                        opt = cur.fetchone()
                        if opt:
                            cur.execute("""
                                INSERT INTO answers (response_id, question_id, selected_option_id)
                                VALUES (%s, %s, %s)
                            """, (response_id, question_id, opt[0]))

                    elif q_type == "multiple_choice":
                        cur.execute("""
                            INSERT INTO answers (response_id, question_id)
                            VALUES (%s, %s)
                            RETURNING id
                        """, (response_id, question_id))
                        ans_id = cur.fetchone()[0]

                        for a in answer:
                            cur.execute("""
                                SELECT id FROM question_options
                                WHERE question_id = %s AND option_text = %s
                            """, (question_id, a))
                            opt = cur.fetchone()
                            if opt:
                                cur.execute("""
                                    INSERT INTO answer_choices (answer_id, option_id)
                                    VALUES (%s, %s)
                                """, (ans_id, opt[0]))

                # Если опрос завершён (нет next_question_id)
                if next_question_id is None:
                    cur.execute("""
                        UPDATE survey_responses
                        SET submitted_at = NOW()
                        WHERE id = %s
                    """, (response_id,))

                conn.commit()
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка при сохранении ответа/обновлении прогресса (SaveAns_UpdateQuest): \n{e}")




# Установка статуса паузы (аналог is_completed_survey = false)
def set_survey_paused(user_id, survey_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Просто убеждаемся, что у пользователя есть активная сессия прохождения
                # Если нет — создаём новую незавершённую запись
                cur.execute("""
                    SELECT id FROM survey_responses
                    WHERE respondent_id = %s AND survey_id = %s AND submitted_at IS NULL
                """, (user_id, survey_id))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO survey_responses (survey_id, respondent_id)
                        VALUES (%s, %s)
                    """, (survey_id, user_id))
                conn.commit()
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка при установке статуса паузы (set_survey_paused): \n{e}")


# Определение текущего вопроса (первый неотвеченный)
def get_current_question_id(user_id, survey_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Получаем все вопросы опроса
                cur.execute("""
                    SELECT id FROM questions
                    WHERE survey_id = %s
                    ORDER BY position
                """, (survey_id,))
                question_ids = [row[0] for row in cur.fetchall()]

                # Находим те, на которые уже отвечено
                cur.execute("""
                    SELECT q.id
                    FROM questions q
                    JOIN answers a ON q.id = a.question_id
                    JOIN survey_responses sr ON a.response_id = sr.id
                    WHERE sr.respondent_id = %s AND q.survey_id = %s AND sr.submitted_at IS NULL
                """, (user_id, survey_id))
                answered = {row[0] for row in cur.fetchall()}

                for qid in question_ids:
                    if qid not in answered:
                        return qid
                return None
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка получения текущего вопроса (get_current_question_id): \n{e}")
        return None


# Получение информации о профиле (статистика пользователя)
def get_profile_info(user_id):
    try:
        conn = connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Подсчитываем завершённые опросы и количество ответов
                cur.execute(
                    '''
                    SELECT
                        (SELECT COUNT(*) 
                         FROM survey_responses
                         WHERE respondent_id = %s AND submitted_at IS NOT NULL) AS surveys_count,
                        (SELECT COUNT(*) 
                         FROM answers a
                         JOIN survey_responses sr ON a.response_id = sr.id
                         WHERE sr.respondent_id = %s) AS answers_count;
                    ''',
                    (user_id, user_id)
                )
                result = cur.fetchone()
                if result:
                    return {
                        "surveys_count": result[0],
                        "answers_count": result[1]
                    }
                return None
        finally:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка получения информации о профиле (get_profile_info): \n{e}")
        return None