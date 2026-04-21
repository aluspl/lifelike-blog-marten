#!/usr/bin/env python3
import json
import os
import sys
import time
import requests
import psycopg2

API_URL = os.environ.get("TESTER_API_URL", "http://localhost:5501")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5533")
DB_NAME = os.environ.get("DB_NAME", "marten")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')
    # pass


def print_header(text):
    print("\n" + "="*60)
    print(f" {text.center(58)} ")
    print("="*60 + "\n")

def wait():
    input("\n[Naciśnij Enter, aby kontynuować...]")

def get_db_conn():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        )
        return conn
    except Exception as e:
        print(f"[DB ERROR] Nie można połączyć się z bazą danych: {e}")
        return None

def show_events(stream_id=None):
    conn = get_db_conn()
    if not conn: return
    try:
        with conn.cursor() as cur:
            query = "SELECT stream_id, version, type, data, timestamp FROM mt_events"
            if stream_id:
                query += f" WHERE stream_id = '{stream_id}'"
            query += " ORDER BY timestamp ASC"
            
            cur.execute(query)
            rows = cur.fetchall()
            print("\n--- [Baza Danych: Tabela mt_events] ---")
            if not rows:
                print("Brak zdarzeń.")
            for row in rows:
                sid, ver, etype, data, ts = row
                print(f"v{ver} | {ts.strftime('%H:%M:%S')} | Type: {etype}")
                print(f"   Data: {json.dumps(data, indent=2)}")
    finally:
        conn.close()

def show_author_stats(author):
    conn = get_db_conn()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT data FROM mt_doc_authorstats WHERE id = '{author}' LIMIT 1")
            row = cur.fetchone()
            print("\n--- [Baza Danych: Projekcja AuthorStats (MultiStream)] ---")
            if row:
                data = row[0]
                if isinstance(data, str): data = json.loads(data)
                print(f"  Autor:           {data.get('Id') or data.get('id')}")
                print(f"  TotalPosts:      {data.get('TotalPosts') or data.get('totalPosts', 0)}")
                print(f"  PublishedPosts:  {data.get('PublishedPosts') or data.get('publishedPosts', 0)}")
                print(f"  Full JSON: {json.dumps(data, indent=2)}")
            else:
                print(f"  Brak danych dla autora '{author}' — projekcja Async może jeszcze przetwarzać zdarzenia.")
    except Exception as e:
        print(f"  [DB INFO] Tabela jeszcze nie istnieje lub błąd: {e}")
    finally:
        conn.close()

def show_projection(post_id):
    conn = get_db_conn()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT data FROM mt_doc_postdetails WHERE id = '{post_id}'")
            row = cur.fetchone()
            print("\n--- [Baza Danych: Projekcja PostDetails] ---")
            if row:
                data = row[0]
                if isinstance(data, str): data = json.loads(data)
                status = "PUBLISHED" if data.get('IsPublished') else "DRAFT"
                print(f"Status: {status} | Tytuł: {data.get('Title')}")
                print(f"   Full JSON: {json.dumps(data, indent=2)}")
            else:
                print("Projekcja jeszcze nie istnieje.")
    finally:
        conn.close()

def run_presentation():
    clear()
    print_header("Marten Blog API - Interaktywna Prezentacja")
    print("Witaj! Ten skrypt pokaże Ci krok po kroku, jak działa Event Sourcing.")
    print("Zaczynamy od sprawdzenia czy API żyje...")
    
    try:
        resp = requests.get(f"{API_URL}/posts", timeout=3)
        if resp.status_code != 200:
            print(f"Błąd API: {resp.status_code}. Czy Docker działa?")
            return
    except Exception as e:
        print(f"Nie można połączyć się z API: {e}")
        return

    print("API OK. Gotowy na demo?")
    wait()

    # --- KROK 1 ---
    clear()
    print_header("KROK 1: Tworzenie pierwszego posta")
    print("Wysyłamy POST /posts. Marten zapisze to jako nowe zdarzenie.")
    
    payload = {
        "title": "Marten to przyszłość",
        "content": "Event Sourcing w .NET 10 jest niesamowity!",
        "author": "Szymon"
    }
    
    print(f"\nRequest Body (POST /posts):\n{json.dumps(payload, indent=2)}")
    resp = requests.post(f"{API_URL}/posts", json=payload)
    print(f"API Response ({resp.status_code}):")
    if resp.content:
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)
    else:
        print("[Empty Response]")
    
    # Pobierzmy ID (najnowszy post)
    posts = requests.get(f"{API_URL}/posts").json()
    post_id = posts[0]['id']
    print(f"\nUtworzono post o ID: {post_id}")
    
    show_events(post_id)
    show_projection(post_id)
    
    print("\nZauważ: W mt_events mamy wersję v1 (PostCreated).")
    wait()

    # --- KROK 2 ---
    clear()
    print_header("KROK 2: Aktualizacja treści")
    print("Wysyłamy PUT /posts/{id}. Zmieniamy tytuł.")
    
    payload["title"] = "Marten to przyszłość (EDYCJA)"
    print(f"\nRequest Body (PUT /posts/{post_id}):\n{json.dumps(payload, indent=2)}")
    resp = requests.put(f"{API_URL}/posts/{post_id}", json=payload)
    print(f"API Response ({resp.status_code}):")
    if resp.content:
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)
    else:
        print("[Empty Response / NoContent]")
    
    show_events(post_id)
    show_projection(post_id)
    
    print("\nZauważ: Mamy teraz wersję v2 (PostUpdated). Projekcja została zaktualizowana.")
    wait()

    # --- KROK 3 ---
    clear()
    print_header("KROK 3: Publikacja")
    print("Wysyłamy POST /posts/{id}/publish. Zmieniamy stan domeny.")
    
    print(f"\nRequest (POST /posts/{post_id}/publish) [No Body]")
    resp = requests.post(f"{API_URL}/posts/{post_id}/publish")
    print(f"API Response ({resp.status_code}):")
    if resp.content:
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)
    else:
        print("[Empty Response / NoContent]")
    
    show_events(post_id)
    show_projection(post_id)
    
    print("\nZauważ: Wersja v3 (PostPublished). Status w projekcji zmienił się na PUBLISHED.")
    wait()

    # --- KROK 4 ---
    clear()
    print_header("KROK 4: Historia Zdarzeń")
    print("Zapytajmy API o historię zmian tego konkretnego obiektu.")
    
    events = requests.get(f"{API_URL}/posts/{post_id}/events").json()
    print(f"\nGET /posts/{post_id}/events:")
    for e in events:
        print(f"  [{e['timestamp']}] {e['eventType']} (ver: {e['version']})")
    
    print("\nTo jest 'Source of Truth'. Z tego można odtworzyć wszystko.")
    wait()

    # --- KROK 5 ---
    clear()
    print_header("KROK 5: Rebuilding (Magia)")
    print("Co jeśli zmienimy definicję projekcji?")
    print("W Martenie możemy 'przepuścić' wszystkie zdarzenia od nowa.")
    
    print("Wysyłamy POST /admin/rebuild...")
    resp = requests.post(f"{API_URL}/admin/rebuild")
    print(f"API Response: {resp.status_code} OK")
    print(json.dumps(resp.json(), indent=2))
    
    print("\nWszystkie modele do odczytu zostały właśnie zbudowane od zera na podstawie historii zdarzeń!")
    wait()

    # --- KROK 6 ---
    clear()
    print_header("KROK 6: MultiStreamProjection — AuthorStats")
    print("Obok SingleStreamProjection, Marten oferuje MultiStreamProjection.")
    print("Zamiast jeden stream → jeden dokument, tutaj WIELE streamów → jeden dokument per klucz.")
    print()
    print("AuthorStats agreguje zdarzenia PostCreated z każdego posta autora 'Szymon'.")
    print("Każdy post żyje w OSOBNYM streamie (inny Guid), ale wszystkie razem tworzą")
    print("jeden dokument AuthorStats dla tego autora.")
    print()
    print("Ta projekcja ma lifecycle=Async, więc daemon przetwarza ją asynchronicznie.")
    print("Czekamy chwilę na daemon...")
    time.sleep(3)

    # Spróbuj przez API (najlepsza metoda)
    try:
        resp = requests.get(f"{API_URL}/stats/authors/Szymon", timeout=5)
        if resp.status_code == 200:
            stats = resp.json()
            print(f"\nGET /stats/authors/Szymon → 200 OK")
            print(f"  TotalPosts:     {stats.get('totalPosts', 0)}")
            print(f"  PublishedPosts: {stats.get('publishedPosts', 0)}")
        elif resp.status_code == 404:
            print("\nGET /stats/authors/Szymon → 404 (daemon jeszcze przetwarza lub brak postów)")
    except Exception:
        pass

    # Zajrzyj też bezpośrednio do bazy danych
    show_author_stats("Szymon")

    print("\nKluczowe różnice:")
    print("  SingleStreamProjection: 1 stream → 1 dokument (PostDetails per post)")
    print("  MultiStreamProjection:  N streamów → 1 dokument (AuthorStats per autor)")
    wait()

    clear()
    print_header("Dziękuję za udział w prezentacji!")
    print("Teraz wiesz jak działa Marten + Event Sourcing.")
    print("Zajrzyj do docs/PRESENTATION.md, aby dowiedzieć się więcej.")

if __name__ == "__main__":
    try:
        run_presentation()
    except KeyboardInterrupt:
        print("\nPrzerwano.")
