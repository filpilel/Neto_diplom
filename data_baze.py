def create_tables(compound):
    with compound.cursor() as cursor:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        vk_id INTEGER NOT NULL UNIQUE,
        first_name VARCHAR(30) NOT NULL,
        last_name VARCHAR(30) NOT NULL,
        age INTEGER NOT NULL,
        city_id INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS result_users(
        id SERIAL PRIMARY KEY,
        vk_id INTEGER NOT NULL UNIQUE,
        user_id INT REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        compound.commit()
        print('Таблицы успешно созданы.')


def delete_tables(compound):
    with compound.cursor() as cursor:
        cursor.execute("""
        DROP TABLE IF EXISTS users CASCADE;
        DROP TABLE IF EXISTS result_users;
        DROP TABLE IF EXISTS search_user CASCADE;
        DROP TABLE IF EXISTS search_user_photo;
        """)
        compound.commit()
        print('Таблицы успешно удалены.')


def insert_user(compound, user_info):
    with compound.cursor() as cursor:
        cursor.execute("""
        select id from users
        where vk_id = %s
        """, (user_info.get('id'),))

        user_data_baze_id = cursor.fetchone()

        if user_data_baze_id is not None:
            return user_data_baze_id[0]

        cursor.execute("""
        insert into users(vk_id, first_name, last_name, age, city_id) values
        (%s, %s, %s, %s, %s) returning id
        """, (user_info.get('id'),
              user_info.get('first_name'),
              user_info.get('last_name'),
              user_info.get('age'),
              user_info.get('city'),))
        user_data_baze_id = cursor.fetchone()[0]
    compound.commit()
    if user_data_baze_id:
        return user_data_baze_id
    else:
        return False


def insert_result_user(compound, user_data_baze_id, finally_selected_user):
    with compound.cursor() as cursor:
        cursor.execute("""
        INSERT INTO result_users(vk_id, user_id) VALUES
        (%s, %s) RETURNING id
        """, (finally_selected_user.get('id'),
              user_data_baze_id,))
    compound.commit()


def get_user_data_baze_id(compound, vk_id):
    with compound.cursor() as cursor:
        cursor.execute("""
        SELECT id FROM users
        WHERE vk_id = %s
        """, (vk_id,))
        user_data_baze_id = cursor.fetchone()
    if user_data_baze_id:
        return user_data_baze_id[0]
    else:
        return False


def check_result_user(compound, user_id, user_data_baze_id):
    with compound.cursor() as cursor:
        cursor.execute("""
        SELECT vk_id FROM result_users
        WHERE vk_id = %s AND user_id = %s
        """, (user_id, user_data_baze_id,))
        result_user_data_baze_id = cursor.fetchone()
    if result_user_data_baze_id is not None:
        return False
    else:
        return True
