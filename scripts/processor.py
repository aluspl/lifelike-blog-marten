import psycopg2
import time
import os
import json

def main():
    # Defaults adjusted for host-side execution (mapped port 5533)
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5533")
    db_name = os.environ.get("DB_NAME", "marten")
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", "postgres")

    conn_str = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_pass}"
    
    print(f"Python Marten Observer starting (connecting to {db_host}:{db_port})...")

    while True:
        try:
            with psycopg2.connect(conn_str) as conn:
                with conn.cursor() as cur:
                    # Marten stores projections in 'mt_doc_[projection_name]'
                    cur.execute("SELECT data FROM public.mt_doc_postdetails;")
                    rows = cur.fetchall()
                    print(f"\n--- [{time.strftime('%H:%M:%S')}] Found {len(rows)} Posts in Marten Table ---")
                    for row in rows:
                        data = row[0]
                        # Handle potential string/dict differences based on driver version
                        if isinstance(data, str):
                            data = json.loads(data)
                        status = "PUBLISHED" if data.get('IsPublished') else "DRAFT"
                        print(f"[{status}] {data.get('Id')} | {data.get('Title')}")
            time.sleep(10)
        except Exception as e:
            print(f"[DATABASE ERROR] {e}")
            print("Is Docker environment running? (check ports 5533)")
            time.sleep(5)

if __name__ == "__main__":
    main()
