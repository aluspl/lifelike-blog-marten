import psycopg2
import time
import os

def main():
    db_host = os.environ.get("DB_HOST", "postgres")
    db_name = os.environ.get("DB_NAME", "marten")
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", "postgres")

    conn_str = f"host={db_host} dbname={db_name} user={db_user} password={db_pass}"
    
    print("Python observer starting... waiting for database")
    time.sleep(5)  # Wait for postgres

    while True:
        try:
            with psycopg2.connect(conn_str) as conn:
                with conn.cursor() as cur:
                    # Marten stores projections in a schema-qualified table
                    # The table name is usually 'mt_doc_postdetails'
                    cur.execute("SELECT data FROM public.mt_doc_postdetails;")
                    rows = cur.fetchall()
                    print(f"--- Python Observer Found {len(rows)} Posts ---")
                    for row in rows:
                        print(row[0])
            time.sleep(10)
        except Exception as e:
            print(f"Error connecting to database: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
