#!/usr/bin/env python3
import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

import requests

# Default API URL (can be overridden via --api-url or env TESTER_API_URL)
API_URL = os.environ.get("TESTER_API_URL", "http://localhost:5501")

# Path to docker-compose directory / file (can be overridden)
DEFAULT_COMPOSE_PATH = os.environ.get("TESTER_COMPOSE_PATH", "docker/docker-compose.yml")
# Fallback candidate locations for docker-compose if the default is missing
CANDIDATE_COMPOSE_FILES = [
    DEFAULT_COMPOSE_PATH,
    os.path.join("docker", "docker-compose.yml"),
    os.path.join("docker", "compose.yml"),
    "docker-compose.yml",
]


DEBUG_MODE = False


def show_menu():
    """Show menu. If DEBUG_MODE is True, show a compact menu (options 1-9 + exit debug)."""
    print("\n--- Marten Blog API Tester ---")
    if DEBUG_MODE:
        print("1. Utwórz nowy wpis (POST /posts)")
        print("2. Wyświetl wszystkie wpisy (GET /posts)")
        print("3. Aktualizuj wpis (PUT /posts/{id})")
        print("4. Opublikuj wpis (POST /posts/{id}/publish)")
        print("5. Cofnij publikację (POST /posts/{id}/unpublish)")
        print("6. Szczegóły wpisu (GET /posts/{id})")
        print("7. Historia zdarzeń (GET /posts/{id}/events)")
        print("8. Admin: Rebuild Projections (POST /admin/rebuild)")
        print("9. Statystyki autora — MultiStream (GET /stats/authors/{autor})")
        print("10. Healthcheck API (debug toggle)")
        print("0. Wyjście z trybu debug (przywróć pełne menu)")
        return input("Wybierz opcję: ")
    else:
        print("1. Utwórz nowy wpis (POST /posts)")
        print("2. Wyświetl wszystkie wpisy (GET /posts)")
        print("3. Aktualizuj wpis (PUT /posts/{id})")
        print("4. Opublikuj wpis (POST /posts/{id}/publish)")
        print("5. Cofnij publikację (POST /posts/{id}/unpublish)")
        print("6. Szczegóły wpisu (GET /posts/{id})")
        print("7. Historia zdarzeń (GET /posts/{id}/events)")
        print("8. Admin: Rebuild Projections (POST /admin/rebuild)")
        print("9. Statystyki autora — MultiStream (GET /stats/authors/{autor})")
        print("10. Healthcheck API")
        print("11. Start isolated env (docker-compose up)")
        print("12. Stop isolated env (docker-compose down)")
        print("13. Show docker-compose logs")
        print("14. Run all (orchestrate: start env -> wait -> run simple scenario)")
        print("15. Wyjście")
        return input("Wybierz opcję: ")

def rebuild_projections():
    try:
        response = requests.post(f"{API_URL}/admin/rebuild")
        if response.status_code == 200:
            print("[SUCCESS] Projekcje zostały przebudowane.")
            print(json.dumps(response.json(), indent=4))
        else:
            print(f"[ERROR] Status: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"[EXCEPTION] {e}")

def get_author_stats():
    """GET /stats/authors/{author} — MultiStreamProjection demo"""
    author = input("Nazwa autora: ").strip()
    if not author:
        print("[ERROR] Podaj nazwę autora.")
        return
    try:
        response = requests.get(f"{API_URL}/stats/authors/{author}")
        if response.status_code == 200:
            stats = response.json()
            print(f"\n[AuthorStats — MultiStreamProjection]")
            print(f"  Autor:            {stats.get('id', '?')}")
            print(f"  Wszystkie posty:  {stats.get('totalPosts', 0)}")
            print(f"  Opublikowane:     {stats.get('publishedPosts', 0)}")
            print(f"\nRaw JSON:\n{json.dumps(stats, indent=4)}")
        elif response.status_code == 404:
            print(f"[NOT FOUND] Brak statystyk dla autora '{author}'. Może projekcja Async jeszcze nie przetworzyła zdarzeń?")
        else:
            print(f"[ERROR] Status: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"[EXCEPTION] {e}")

def create_post():
    title = input("Tytuł: ")
    content = input("Treść: ")
    author = input("Autor: ")
    
    payload = {
        "title": title,
        "content": content,
        "author": author
    }
    
    try:
        print(f"Request Body (POST /posts):\n{json.dumps(payload, indent=2)}")
        response = requests.post(f"{API_URL}/posts", json=payload)
        print(f"API Response ({response.status_code}):")
        if response.content:
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text)
        else:
            print("[Empty Response]")

        if response.status_code == 202:
            print("[SUCCESS] Komenda utworzenia wysłana (202 Accepted).")
        else:
            print(f"[ERROR] Status: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"[EXCEPTION] {e}")

def update_post():
    posts = list_posts()
    if not posts: return
    
    idx = int(input("Wybierz numer wpisu do aktualizacji: ")) - 1
    post_id = posts[idx]['id']
    
    title = input(f"Nowy tytuł (obecny: {posts[idx]['title']}): ")
    content = input("Nowa treść: ")
    
    payload = {
        "id": post_id,
        "title": title,
        "content": content
    }
    
    try:
        print(f"Request Body (PUT /posts/{post_id}):\n{json.dumps(payload, indent=2)}")
        response = requests.put(f"{API_URL}/posts/{post_id}", json=payload)
        print(f"API Response ({response.status_code}):")
        if response.content:
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text)
        else:
            print("[Empty Response / NoContent]")

        if response.status_code == 204:
            print(f"[SUCCESS] Wpis {post_id} został zaktualizowany.")
        else:
            print(f"[ERROR] Status: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"[EXCEPTION] {e}")

def list_posts():
    try:
        response = requests.get(f"{API_URL}/posts")
        if response.status_code == 200:
            posts = response.json()
            if not posts:
                print("Brak wpisów.")
                return []
            
            print("\n--- Lista wpisów ---")
            for i, post in enumerate(posts):
                status = "OPUBLIKOWANY" if post['isPublished'] else "SZKIC"
                print(f"{i+1}. [{status}] ID: {post['id']} | Tytuł: {post['title']}")
            return posts
        elif response.status_code == 403:
            print(f"[ERROR] Status: {response.status_code} - Forbidden. API may be configured to deny access.")
            ans = input("Uruchomic izolowane srodowisko przez docker-compose? [y/N]: ")
            if ans.lower().startswith('y'):
                compose_file = DEFAULT_COMPOSE_PATH
                ok_up, out = compose_up(compose_file)
                if not ok_up:
                    print(f"[DOCKER] compose up failed:\n{out}")
                    return []
                print("[DOCKER] compose up started, czekam na zdrowie API...")
                ok_wait, details = api_health(API_URL, retries=30, delay=2)
                if not ok_wait:
                    print(f"[ORCH] API did not become healthy: {details}")
                    print(compose_logs(compose_file))
                    return []
                # retry request once
                try:
                    response2 = requests.get(f"{API_URL}/posts")
                    if response2.status_code == 200:
                        posts = response2.json()
                        if not posts:
                            print("Brak wpisów.")
                            return []
                        print("\n--- Lista wpisów ---")
                        for i, post in enumerate(posts):
                            status = "OPUBLIKOWANY" if post['isPublished'] else "SZKIC"
                            print(f"{i+1}. [{status}] ID: {post['id']} | Tytuł: {post['title']}")
                            # persist chosen post id to .env-like file for later viewing
                            try:
                                env_path = os.path.join(os.getcwd(), "scripts", ".tester_env")
                                with open(env_path, "a", encoding="utf-8") as fh:
                                    fh.write(f"LAST_LISTED_POST={post['id']}\n")
                            except Exception:
                                pass
                        return posts
                    else:
                        print(f"[ERROR] Status after compose: {response2.status_code}")
                        return []
                except Exception as e:
                    print(f"[EXCEPTION] After compose retry: {e}")
                    return []
            else:
                return []
        else:
            print(f"[ERROR] Status: {response.status_code}")
            return []
    except Exception as e:
        print(f"[EXCEPTION] {e}")
        return []

def publish_post():
    posts = list_posts()
    if not posts: return
    
    idx = int(input("Wybierz numer wpisu do opublikowania: ")) - 1
    post_id = posts[idx]['id']
    
    try:
        response = requests.post(f"{API_URL}/posts/{post_id}/publish")
        if response.status_code == 204:
            print(f"[SUCCESS] Wpis {post_id} został opublikowany.")
        else:
            print(f"[ERROR] Status: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"[EXCEPTION] {e}")

def unpublish_post():
    posts = list_posts()
    if not posts: return
    
    idx = int(input("Wybierz numer wpisu, aby cofnąć publikację: ")) - 1
    post_id = posts[idx]['id']
    
    try:
        response = requests.post(f"{API_URL}/posts/{post_id}/unpublish")
        if response.status_code == 204:
            print(f"[SUCCESS] Publikacja wpisu {post_id} została cofnięta.")
        else:
            print(f"[ERROR] Status: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"[EXCEPTION] {e}")

def view_details():
    posts = list_posts()
    if not posts: return
    
    idx = int(input("Wybierz numer wpisu: ")) - 1
    post_id = posts[idx]['id']
    
    try:
        response = requests.get(f"{API_URL}/posts/{post_id}")
        if response.status_code == 200:
            print("\n--- Szczegóły ---")
            print(json.dumps(response.json(), indent=4))
        else:
            print(f"[ERROR] Status: {response.status_code}")
    except Exception as e:
        print(f"[EXCEPTION] {e}")

def view_events():
    posts = list_posts()
    if not posts: return
    
    idx = int(input("Wybierz numer wpisu, aby zobaczyć historię: ")) - 1
    post_id = posts[idx]['id']
    
    try:
        response = requests.get(f"{API_URL}/posts/{post_id}/events")
        if response.status_code == 200:
            events = response.json()
            print(f"\n--- Historia zdarzeń dla {post_id} ---")
            for e in events:
                print(f"v{e['version']} | {e['timestamp']} | {e['eventType']}")
                print(f"   Data: {json.dumps(e['data'])}")
        else:
            print(f"[ERROR] Status: {response.status_code}")
    except Exception as e:
        print(f"[EXCEPTION] {e}")


def create_post_noninteractive(title: str, content: str, author: str) -> dict | None:
    payload = {"title": title, "content": content, "author": author}
    try:
        r = requests.post(f"{API_URL}/posts", json=payload, timeout=5)
        if r.status_code in (200, 201, 202):
            try:
                return r.json() if r.content else {"status": r.status_code}
            except Exception:
                return {"status": r.status_code}
        return None
    except requests.RequestException:
        return None


def update_post_noninteractive(post_id: str, title: str, content: str) -> bool:
    payload = {"id": post_id, "title": title, "content": content}
    try:
        r = requests.put(f"{API_URL}/posts/{post_id}", json=payload, timeout=5)
        return r.status_code in (200, 204)
    except requests.RequestException:
        return False


def publish_post_noninteractive(post_id: str) -> bool:
    try:
        r = requests.post(f"{API_URL}/posts/{post_id}/publish", timeout=5)
        return r.status_code in (200, 204)
    except requests.RequestException:
        return False


def unpublish_post_noninteractive(post_id: str) -> bool:
    try:
        r = requests.post(f"{API_URL}/posts/{post_id}/unpublish", timeout=5)
        return r.status_code in (200, 204)
    except requests.RequestException:
        return False


def get_post_noninteractive(post_id: str) -> dict | None:
    try:
        r = requests.get(f"{API_URL}/posts/{post_id}", timeout=5)
        if r.status_code == 200:
            return r.json()
        return None
    except requests.RequestException:
        return None


def get_events_noninteractive(post_id: str) -> list | None:
    try:
        r = requests.get(f"{API_URL}/posts/{post_id}/events", timeout=5)
        if r.status_code == 200:
            return r.json()
        return None
    except requests.RequestException:
        return None


def test_flows_1_to_5(auto_start: bool = True, compose_file: str | None = None, no_teardown: bool = False) -> dict:
    """Programmatically run flows 1-5: create, list, publish, get, events.

    Returns a dict with results and errors.
    """
    result: dict = {"create": None, "list": None, "publish": None, "get": None, "events": None, "errors": []}
    started_compose = False

    def ensure_api():
        ok, _ = api_health(API_URL, retries=2, delay=1)
        if ok:
            return True
        if auto_start:
            ok_up, out = compose_up(compose_file)
            if not ok_up:
                result["errors"].append(f"compose_up failed: {out}")
                return False
            nonlocal started_compose
            started_compose = True
            ok_wait, details = api_health(API_URL, retries=30, delay=2)
            if not ok_wait:
                result["errors"].append(f"API did not become healthy: {details}")
                # attempt to capture logs
                try:
                    result["compose_logs"] = compose_logs(compose_file)
                except Exception:
                    pass
                return False
            return True
        result["errors"].append("API not healthy and auto_start disabled")
        return False

    if not ensure_api():
        return result

    # 1. Create
    created = create_post_noninteractive("E2E test - flows 1-5", "content", "tester")
    result["create"] = created
    if not created:
        result["errors"].append("create failed")
        if started_compose and not no_teardown:
            compose_down(compose_file)
        return result

    # 2. List
    posts = list_posts()
    result["list"] = posts
    post_id = None
    if posts:
        for p in posts:
            if p.get("title") == "E2E test - flows 1-5":
                post_id = p.get("id")
                break
    if not post_id:
        if isinstance(created, dict):
            post_id = created.get("id")
    if not post_id:
        result["errors"].append("could not determine post id after create/list")
        if started_compose and not no_teardown:
            compose_down(compose_file)
        return result

    # 3. Publish
    ok_pub = publish_post_noninteractive(post_id)
    result["publish"] = ok_pub
    if not ok_pub:
        result["errors"].append("publish failed")

    # 4. Get
    got = None
    try:
        got = requests.get(f"{API_URL}/posts/{post_id}", timeout=5)
        if got.status_code == 200:
            result["get"] = got.json()
        else:
            result["get"] = None
            result["errors"].append(f"get status: {got.status_code}")
    except Exception as e:
        result["errors"].append(f"get exception: {e}")

    # 5. Events
    ev = get_events_noninteractive(post_id)
    result["events"] = ev
    if ev is None:
        result["errors"].append("events failed")

    if started_compose and not no_teardown:
        try:
            compose_down(compose_file)
        except Exception:
            pass

    return result

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    global DEBUG_MODE, API_URL
    # Ensure DEBUG_MODE is treated as module global before any reference
    print(f"Łączenie z API pod adresem: {API_URL}")

    # If there is a compose file available, try to discover the mapped host
    # port and prefer that API URL. This prevents the script from reporting
    # localhost:5000 when compose maps to a different host port (eg. 5001).
    compose_candidate = select_compose_file(None)
    if compose_candidate:
        discovered = discover_api_url_from_compose(compose_candidate)
        if discovered:
            API_URL = discovered
            print(f"[STARTUP] Discovered API URL from compose: {API_URL}")

    # Run a startup healthcheck. If the API is not healthy, try to start the
    # local docker-compose environment and wait for the API to become healthy.
    ok, details = api_health(API_URL, retries=3, delay=1)
    if not ok:
        print("[STARTUP] API not healthy on startup — attempting to start docker-compose...")
        # allow compose_up to discover fallback compose files by passing None
        compose_file = DEFAULT_COMPOSE_PATH if os.path.exists(DEFAULT_COMPOSE_PATH) else None
        ok_up, out = compose_up(compose_file)
        if not ok_up:
            print(f"[STARTUP] compose up failed: {out}")
            print("[STARTUP] Cannot continue without a healthy API. Exiting.")
            return
        print("[STARTUP] compose up started; waiting for API to become healthy...")
        ok_wait, details = api_health(API_URL, retries=30, delay=2)
        if not ok_wait:
            print(f"[STARTUP] API did not become healthy: {details}")
            print("[STARTUP] Showing recent compose logs:\n")
            try:
                print(compose_logs(compose_file))
            except Exception:
                pass
            print("[STARTUP] Cannot continue without a healthy API. Exiting.")
            return
        print("[STARTUP] API is healthy — continuing to interactive menu.")

    while True:
        try:
            choice = show_menu()
            if DEBUG_MODE:
                if choice == '1':
                    create_post()
                elif choice == '2':
                    list_posts()
                elif choice == '3':
                    update_post()
                elif choice == '4':
                    publish_post()
                elif choice == '5':
                    unpublish_post()
                elif choice == '6':
                    view_details()
                elif choice == '7':
                    view_events()
                elif choice == '8':
                    rebuild_projections()
                elif choice == '9':
                    get_author_stats()
                elif choice == '10':
                    # toggle debug off -> return full menu
                    print("Exiting debug mode")
                    DEBUG_MODE = False
                elif choice == '0':
                    print("Exiting debug mode")
                    DEBUG_MODE = False
                else:
                    if choice != '':
                        print("Nieprawidłowa opcja (debug).")
            else:
                if choice == '1':
                    create_post()
                elif choice == '2':
                    list_posts()
                elif choice == '3':
                    update_post()
                elif choice == '4':
                    publish_post()
                elif choice == '5':
                    unpublish_post()
                elif choice == '6':
                    view_details()
                elif choice == '7':
                    view_events()
                elif choice == '8':
                    rebuild_projections()
                elif choice == '9':
                    get_author_stats()
                elif choice == '10':
                    ok, details = api_health(API_URL)
                    if ok:
                        print(f"[HEALTH] API reachable: {details}")
                    else:
                        print(f"[HEALTH] API not reachable: {details}")
                elif choice == '11':
                    compose_file = DEFAULT_COMPOSE_PATH
                    ok, out = compose_up(compose_file)
                    if ok:
                        print("[DOCKER] compose up started")
                    else:
                        print(f"[DOCKER] compose up failed:\n{out}")
                elif choice == '12':
                    compose_file = DEFAULT_COMPOSE_PATH
                    ok, out = compose_down(compose_file)
                    if ok:
                        print("[DOCKER] compose down finished")
                    else:
                        print(f"[DOCKER] compose down failed:\n{out}")
                elif choice == '13':
                    compose_file = DEFAULT_COMPOSE_PATH
                    out = compose_logs(compose_file)
                    print(out)
                elif choice == '14':
                    run_all_orchestrate()
                elif choice == '15':
                    print("Koniec.")
                    break
                else:
                    if choice != '':
                        print("Nieprawidłowa opcja.")

            if choice not in ('15', ''):
                input("\nNaciśnij Enter, aby kontynuować...")
                clear_screen()
            elif choice == '':
                clear_screen()

        except KeyboardInterrupt:
            print("\nPrzerwano przez użytkownika (Ctrl+C). Wyjście...")
            break


def api_health(api_url, retries=5, delay=2):
    """Simple HTTP healthcheck for the API."""
    last_err = None
    for i in range(retries):
        try:
            t0 = time.time()
            resp = requests.get(f"{api_url}/posts", timeout=3)
            latency = time.time() - t0
            if 200 <= resp.status_code < 300 or resp.status_code in (202, 204):
                return True, {"status": resp.status_code, "latency": latency}
            last_err = f"status={resp.status_code} body={resp.text}"
        except Exception as e:
            last_err = str(e)
        time.sleep(delay)
    return False, {"error": last_err}


def select_compose_file(preferred: str | None = None) -> str | None:
    """Pick the compose file to use. Prefer `preferred` if it exists, otherwise
    search CANDIDATE_COMPOSE_FILES in order and return the first existing path.
    """
    if preferred and os.path.exists(preferred):
        return preferred
    for candidate in CANDIDATE_COMPOSE_FILES:
        if not candidate:
            continue
        if os.path.exists(candidate):
            return candidate
    return None


def db_tcp_health(host="localhost", port=5432, timeout=2):
    """Check TCP connectivity to a host:port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True, None
    except Exception as e:
        return False, str(e)


def run_subprocess(cmd, cwd=None, env=None, timeout=None):
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        out = p.stdout + "\n" + p.stderr
        # write subprocess output to logs
        try:
            from scripts import logs as _logs
            _logs.write_log("subprocess", out)
        except Exception:
            pass
        return p.returncode == 0, out
    except subprocess.TimeoutExpired as te:
        return False, f"Timeout: {te}"
    except Exception as e:
        return False, str(e)


COMPOSE_META = os.path.join(tempfile.gettempdir(), "tester_compose_meta.json")


def _write_compose_meta(base, override):
    info = {"base": base, "override": override}
    try:
        with open(COMPOSE_META, "w", encoding="utf-8") as fh:
            json.dump(info, fh)
    except Exception:
        pass


def _read_compose_meta():
    if not os.path.exists(COMPOSE_META):
        return {}
    try:
        with open(COMPOSE_META, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def is_port_free(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        s.close()
        return True
    except OSError:
        return False


def compose_up(compose_file, service_port_map=None):
    """Run docker compose up. If service_port_map provided, generate an override to remap host ports."""
    # If a compose_file was explicitly provided, respect it and fail if missing.
    if compose_file:
        if not os.path.exists(compose_file):
            return False, f"Compose file not found: {compose_file}"
    else:
        # try common fallbacks
        found = None
        tried = []
        for candidate in CANDIDATE_COMPOSE_FILES:
            if not candidate:
                continue
            tried.append(candidate)
            if os.path.exists(candidate):
                found = candidate
                break
        if found:
            compose_file = found
        else:
            return False, f"Compose file not found. Tried: {', '.join(tried)}. Set TESTER_COMPOSE_PATH or pass --compose-file to point to your compose file."
    override_path = None
    if service_port_map:
        try:
            from scripts.compose_override import generate_override
            override_path = generate_override(service_port_map)
        except Exception as e:
            return False, f"Failed to generate override: {e}"

    cmd = ["docker", "compose", "-f", compose_file]
    if override_path:
        cmd += ["-f", override_path]
    cmd += ["up", "-d"]
    ok, out = run_subprocess(cmd)
    if ok:
        _write_compose_meta(compose_file, override_path)
    return ok, out


def compose_down(compose_file=None, remove_volumes=False):
    meta = _read_compose_meta()
    files = []
    if compose_file:
        files.append(compose_file)
    elif "base" in meta:
        files.append(meta["base"])
    if "override" in meta and meta["override"]:
        files.append(meta["override"])
    if not files:
        return False, "No compose file info found"
    cmd = ["docker", "compose"]
    for f in files:
        cmd += ["-f", f]
    cmd += ["down"]
    if remove_volumes:
        cmd.append("--volumes")
    ok, out = run_subprocess(cmd)
    # cleanup meta if down succeeded
    if ok and os.path.exists(COMPOSE_META):
        try:
            os.remove(COMPOSE_META)
        except Exception:
            pass
    return ok, out


def compose_logs(compose_file, tail=200):
    # If compose_file not provided, try to read last used compose from meta
    if not compose_file:
        meta = _read_compose_meta()
        compose_file = meta.get("base")
        if not compose_file:
            return "Compose file not found: None"
    if not os.path.exists(compose_file):
        return f"Compose file not found: {compose_file}"
    cmd = ["docker", "compose", "-f", compose_file, "logs", "--no-color", f"--tail={tail}"]
    ok, out = run_subprocess(cmd)
    return out


def _parse_port_from_compose_ps(ps_output: str, container_port: int = 8080) -> int | None:
    """Parse docker compose ps output and return the first host port mapped to container_port.

    Looks for patterns like '0.0.0.0:5001->8080/tcp' and returns 5001.
    """
    import re
    # find all occurrences like 0.0.0.0:5001->8080
    matches = re.findall(r"0\.0\.0\.0:(\d+)->%d" % container_port, ps_output)
    if matches:
        try:
            return int(matches[0])
        except Exception:
            return None
    # also try [::]:5001->8080
    matches = re.findall(r"\[::\]:(\d+)->%d" % container_port, ps_output)
    if matches:
        try:
            return int(matches[0])
        except Exception:
            return None
    return None


def discover_api_url_from_compose(compose_file: str | None) -> str | None:
    """Inspect docker compose ps and return API URL (http://localhost:PORT) if found."""
    if not compose_file:
        meta = _read_compose_meta()
        compose_file = meta.get("base")
    if not compose_file or not os.path.exists(compose_file):
        return None
    ok, out = run_subprocess(["docker", "compose", "-f", compose_file, "ps"]) 
    if not ok:
        return None
    port = _parse_port_from_compose_ps(out, container_port=8080)
    if port:
        return f"http://localhost:{port}"
    return None


def show_system_status(compose_file):
    """Prints API health and docker compose ps status (if compose file exists)."""
    ok_api, details = api_health(API_URL, retries=1, delay=0)
    print(f"API health: {'OK' if ok_api else 'DOWN'} -> {details}")
    # docker compose ps — if compose_file is None, consult the compose meta
    if not compose_file:
        meta = _read_compose_meta()
        compose_file = meta.get("base")
    if compose_file and os.path.exists(compose_file):
        print("\nDocker compose ps:")
        ok, out = run_subprocess(["docker", "compose", "-f", compose_file, "ps"])
        print(out)
    else:
        print("Docker compose file not found for ps: ", compose_file)

def run_all_orchestrate(no_teardown=False):
    """Simple orchestration: ensure API is up (start if needed), run scenario, teardown if started."""
    compose_file = DEFAULT_COMPOSE_PATH if os.path.exists(DEFAULT_COMPOSE_PATH) else None
    print("[ORCH] Checking API health...")
    ok, _ = api_health(API_URL, retries=2, delay=1)
    
    started_by_us = False
    if ok:
        print("[ORCH] API already up.")
    else:
        print("[ORCH] API down -> starting isolated environment via docker-compose...")
        ok_up, out = compose_up(compose_file)
        if not ok_up:
            print(f"[ORCH] compose up failed:\n{out}")
            return
        started_by_us = True
        print("[ORCH] compose up OK, waiting for API to become healthy...")
        ok_wait, details = api_health(API_URL, retries=30, delay=2)
        if not ok_wait:
            print(f"[ORCH] API did not become healthy: {details}")
            print("[ORCH] Showing compose logs:\n")
            print(compose_logs(compose_file))
            return

    print("[ORCH] Running full flow scenario...")
    try:
        title = f"Flow Test {int(time.time())}"
        print(f"1. Tworzenie wpisu: {title}")
        create_post_noninteractive(title, "Treść testowa", "orchestrator")
        
        print("2. Pobieranie listy wpisów")
        posts = list_posts()
        post_id = next((p['id'] for p in posts if p['title'] == title), None)
        if not post_id:
            print("[ORCH] Nie znaleziono utworzonego wpisu na liście!")
            return

        print(f"3. Szczegóły (stan początkowy):")
        details = get_post_noninteractive(post_id)
        print(json.dumps(details, indent=2))

        print(f"4. Aktualizowanie wpisu: {post_id}")
        update_post_noninteractive(post_id, f"{title} (UPDATED)", "Zaktualizowana treść")

        print(f"5. Szczegóły (po aktualizacji):")
        details = get_post_noninteractive(post_id)
        print(json.dumps(details, indent=2))

        print(f"6. Publikowanie wpisu: {post_id}")
        publish_post_noninteractive(post_id)

        print(f"7. Szczegóły (po publikacji):")
        details = get_post_noninteractive(post_id)
        print(json.dumps(details, indent=2))

        print(f"8. Cofanie publikacji: {post_id}")
        unpublish_post_noninteractive(post_id)

        print(f"9. Szczegóły (po cofnięciu publikacji):")
        details = get_post_noninteractive(post_id)
        print(json.dumps(details, indent=2))

        print(f"10. Historia zdarzeń:")
        events = get_events_noninteractive(post_id)
        if events:
            for e in events:
                print(f"   v{e['version']} | {e['timestamp']} | {e['eventType']}")
        else:
            print("   Brak zdarzeń.")

    except Exception as e:
        print(f"[ORCH] scenario failed: {e}")

    # Show system status
    print("\n--- System status ---")
    show_system_status(compose_file)
    print("--- End status ---\n")

    if started_by_us:
        try:
            input("Naciśnij Enter aby kontynuować (teardown zostanie wykonany)...")
        except Exception:
            pass
        if not no_teardown:
            print("[ORCH] Tearing down compose environment...")
            ok_down, out_down = compose_down(compose_file)
            if ok_down:
                print("[ORCH] Teardown finished.")
            else:
                print(f"[ORCH] Teardown failed:\n{out_down}")
    else:
        print("[ORCH] API was not started by us, skipping teardown.")

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Marten Blog API tester CLI")
    parser.add_argument("--api-url", "-a", default=os.environ.get("TESTER_API_URL", API_URL), help="Base URL for API")
    parser.add_argument("--compose-file", "-c", default=os.environ.get("TESTER_COMPOSE_PATH", DEFAULT_COMPOSE_PATH), help="Path to docker-compose.yml")
    parser.add_argument("--action", "-x", choices=["health","compose-up","compose-down","compose-logs","run-all","create-post","list-posts","run-scenario","presentation"], help="Non-interactive action to run")
    parser.add_argument("--no-teardown", action="store_true", help="When running orchestration, do not teardown compose")
    parser.add_argument("--in-container", action="store_true", help="Run scenarios/tests inside container runner if available")
    parser.add_argument("--scenario-file", "-s", default=os.path.join("scripts","scenarios","example.yaml"), help="Path to scenario YAML file")
    return parser.parse_args(argv)


def run_with_args(ns):
    global API_URL, DEFAULT_COMPOSE_PATH
    API_URL = ns.api_url
    DEFAULT_COMPOSE_PATH = ns.compose_file
    if ns.action == "health":
        ok, details = api_health(API_URL)
        print("OK" if ok else "FAIL", details)
        return 0 if ok else 2
    if ns.action == "compose-up":
        ok, out = compose_up(DEFAULT_COMPOSE_PATH)
        print(out)
        return 0 if ok else 3
    if ns.action == "compose-down":
        ok, out = compose_down(DEFAULT_COMPOSE_PATH, remove_volumes=not ns.no_teardown)
        print(out)
        return 0 if ok else 3
    if ns.action == "compose-logs":
        out = compose_logs(DEFAULT_COMPOSE_PATH)
        print(out)
        return 0
    if ns.action == "run-all":
        run_all_orchestrate(no_teardown=ns.no_teardown)
        return 0
    if ns.action == "run-scenario":
        try:
            from scripts import scenario_runner as sr
        except Exception as e:
            print("Scenario runner not available:", e)
            return 4
        try:
            scenario = sr.load_scenario(ns.scenario_file)
            scenario = sr.normalize_scenario(scenario)
            summary = sr.execute_scenario(scenario, API_URL)
            print("Scenario summary:", summary)
            # return non-zero if any step failed
            failed = any(not s.get("ok", False) for s in summary.get("steps", []))
            return 0 if not failed else 5
        except FileNotFoundError:
            print("Scenario file not found:", ns.scenario_file)
            return 3
        except Exception as e:
            print("Error running scenario:", e)
            return 4
    if ns.action == "create-post":
        create_post()
        return 0
    if ns.action == "list-posts":
        list_posts()
        return 0
    if ns.action == "presentation":
        try:
            from scripts import presentation_guide as pg
            pg.run_presentation()
            return 0
        except Exception as e:
            print("Error running presentation:", e)
            return 6
    print("No action specified")
    return 1


if __name__ == "__main__":
    # non-interactive if arguments provided
    if len(sys.argv) > 1:
        try:
            ns = parse_args()
            rc = run_with_args(ns)
            sys.exit(rc)
        except SystemExit:
            raise
        except Exception as e:
            print("Fatal error:", e)
            sys.exit(99)
    else:
        main()
