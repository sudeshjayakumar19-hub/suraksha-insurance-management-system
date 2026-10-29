import urllib.request
import urllib.parse
import http.cookiejar
import re
import threading
from bs4 import BeautifulSoup
from config import Config


class DatabaseConnectionError(ConnectionError):
    """Raised when unable to reach or authenticate with the Oracle database bridge."""
    pass


class OracleConnection:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(OracleConnection, cls).__new__(cls)
                cls._instance._init_state()
            return cls._instance

    def _init_state(self):
        """
        Initializes connection state lazily.
        No network requests or database logins are performed during module import.
        """
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.logged_in = False

    def _get_config(self):
        """Retrieve the latest database configuration from Config."""
        return {
            "username": Config.ORACLE_USER,
            "password": Config.ORACLE_PASSWORD,
            "connect_id": Config.ORACLE_CONNECT_ID,
            "base_url": Config.ISQLPLUS_URL,
        }

    def _login(self):
        """
        Authenticate with the Oracle iSQL*Plus bridge.
        Lazy connection executed only when a database query is requested.
        Never reveals credentials, passwords, or connection tokens in exceptions.
        """
        cfg = self._get_config()
        username = cfg["username"]
        password = cfg["password"]
        connect_id = cfg["connect_id"]
        base_url = cfg["base_url"]

        if not base_url:
            self.logged_in = False
            raise DatabaseConnectionError(
                "Oracle database bridge URL is not configured. Please verify ORACLE_HOST and ORACLE_PORT settings."
            )

        if not username or not password:
            self.logged_in = False
            raise DatabaseConnectionError(
                "Oracle database credentials are not configured in environment variables."
            )

        login_url = f"{base_url}/login.uix"
        login_data = urllib.parse.urlencode({
            "username": username,
            "password": password,
            "connectID": connect_id,
            "event": "login"
        }).encode("utf-8")

        try:
            resp = self.opener.open(login_url, data=login_data, timeout=8)
            content = resp.read().decode("utf-8", errors="replace")
            # Verify authentication success pattern
            if "SCOTT@orcl" in content or "Connected as" in content or f"{username.upper()}@{connect_id}" in content:
                self.logged_in = True
            else:
                self.logged_in = False
                m_err = re.search(r"(ORA-\d{5}:[^\n<]+)", content)
                err_detail = f": {m_err.group(1)}" if m_err else ""
                raise DatabaseConnectionError(f"Oracle authentication failed{err_detail}")
        except DatabaseConnectionError:
            self.logged_in = False
            raise
        except Exception:
            self.logged_in = False
            raise DatabaseConnectionError(
                "Unable to connect to Oracle 10g database bridge. The service is temporarily unreachable."
            )

    def test_connection(self):
        """
        Safely tests Oracle connectivity without raising uncaught exceptions.
        Returns True if connected and responsive, False otherwise.
        """
        try:
            with self._lock:
                if not self.logged_in:
                    self._login()
            val = self.execute_scalar("SELECT 1 FROM DUAL", default=0)
            return val == 1 or val == "1"
        except Exception:
            return False

    def execute_query(self, sql):
        with self._lock:
            if not self.logged_in:
                self._login()

            cfg = self._get_config()
            base_url = cfg["base_url"]
            if not base_url:
                raise DatabaseConnectionError("Oracle database bridge is not configured.")

            sql_clean = sql.strip()
            if not sql_clean.endswith(";"):
                sql_clean += ";"

            work_url = f"{base_url}/workspace.uix"
            post_data = urllib.parse.urlencode({"script": sql_clean, "event": "execute"}).encode("utf-8")

            try:
                resp = self.opener.open(work_url, data=post_data, timeout=15)
                content = resp.read().decode("utf-8", errors="replace")
            except Exception:
                # Retry once after re-authenticating
                try:
                    self._login()
                    resp = self.opener.open(work_url, data=post_data, timeout=15)
                    content = resp.read().decode("utf-8", errors="replace")
                except Exception:
                    self.logged_in = False
                    raise DatabaseConnectionError(
                        "Communication with the Oracle database bridge failed. The service may be offline."
                    )

            # Check if session timed out and redirected to login page
            if "login.uix" in resp.geturl() or ("connectID" in content and "Login" in content):
                try:
                    self._login()
                    resp = self.opener.open(work_url, data=post_data, timeout=15)
                    content = resp.read().decode("utf-8", errors="replace")
                except Exception:
                    self.logged_in = False
                    raise DatabaseConnectionError(
                        "Oracle database session expired and re-authentication was unsuccessful."
                    )

            m_err = re.search(r"(ORA-\d{5}:[^\n<]+)", content)
            if m_err:
                raise RuntimeError(m_err.group(1))

            soup = BeautifulSoup(content, "html.parser")
            out_div = soup.find("div", class_="output")
            if not out_div:
                return []

            tables = out_div.find_all("table")
            if not tables:
                return []

            target_table = tables[-1]
            headers = [re.sub(r"\s+", " ", th.get_text(strip=True)).lower() for th in target_table.find_all("th")]

            rows = []
            for tr in target_table.find_all("tr"):
                tds = [re.sub(r"\s+", " ", td.get_text(strip=True)) for td in tr.find_all("td")]
                if tds:
                    if not headers:
                        headers = [f"col_{i+1}" for i in range(len(tds))]
                    row_dict = {}
                    for i in range(min(len(headers), len(tds))):
                        row_dict[headers[i]] = tds[i]
                    # ignore 'no rows selected'
                    if "no rows selected" not in " ".join(tds).lower():
                        rows.append(row_dict)

            return rows

    def execute_scalar(self, sql, default=None):
        rows = self.execute_query(sql)
        if rows and len(rows) > 0:
            first_row = rows[0]
            if first_row:
                return list(first_row.values())[0]
        return default

    def execute_single_row(self, sql):
        rows = self.execute_query(sql)
        if rows and len(rows) > 0:
            return rows[0]
        return None


# Lazy singleton instance
db = OracleConnection()

def query(sql):
    return db.execute_query(sql)

def query_scalar(sql, default=0):
    val = db.execute_scalar(sql, default)
    try:
        if isinstance(val, str) and (val.replace(".", "", 1).isdigit() or (val.startswith("-") and val[1:].replace(".", "", 1).isdigit())):
            return float(val) if "." in val else int(val)
    except:
        pass
    return val

def query_one(sql):
    return db.execute_single_row(sql)

def execute_dml(sql):
    """
    Executes INSERT, UPDATE, or DELETE statement followed by explicit COMMIT.
    Returns True on success or raises RuntimeError / DatabaseConnectionError on error.
    """
    sql_clean = sql.strip()
    if not sql_clean.endswith(";"):
        sql_clean += ";"
    if "commit;" not in sql_clean.lower():
        sql_clean += "\nCOMMIT;"
    db.execute_query(sql_clean)
    return True
