import random
from faker import Faker
# Import PostgreSQL connector if you're not using Django ORM
import psycopg2

# Connect to PostgreSQL server
conn = psycopg2.connect(
    dbname='app_macky',
    user='postgres',
    password='postgres',
    host='0.0.0.0',
    port='5432'
)


fake = Faker()

# Create a cursor object
cur = conn.cursor()

# Execute insert statements
cur.execute("INSERT INTO your_table_name (column1, column2) VALUES (%s, %s)", ('value1', 'value2'))

# Commit the transaction
conn.commit()

# Close cursor and connection
cur.close()
conn.close()




