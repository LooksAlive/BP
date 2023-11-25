from django.db import connection

# database name: app_macky

def execute_raw_sql_query():
    with connection.cursor() as cursor:
        # Execute a simple SQL query
        cursor.execute("SELECT * FROM myapp_cat")

        # Fetch one row
        row = cursor.fetchone()
        print(row)

        # Fetch all rows
        rows = cursor.fetchall()
        print(rows)

