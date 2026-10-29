import urllib.request
import urllib.parse
import http.cookiejar
import re
import threading
from bs4 import BeautifulSoup
from config import Config

class OracleConnection:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(OracleConnection, cls).__new__(cls)
                cls._instance._init_bridge()
            return cls._instance

    def _init_bridge(self):
        self.username = Config.ORACLE_USER
        self.password = Config.ORACLE_PASSWORD
        self.connect_id = Config.ORACLE_CONNECT_ID
        self.base_url = Config.ISQLPLUS_URL
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.logged_in = False
        self._login()

    def _login(self):
        login_url = f"{self.base_url}/login.uix"
        login_data = urllib.parse.urlencode({
            "username": self.username,
            "password": self.password,
            "connectID": self.connect_id,
            "event": "login"
        }).encode("utf-8")
        try:
            resp = self.opener.open(login_url, data=login_data, timeout=10)
            content = resp.read().decode("utf-8", errors="replace")
            if "SCOTT@orcl" in content or "Connected as" in content:
                self.logged_in = True
            else:
                self.logged_in = False
        except Exception as e:
            self.logged_in = False
            raise ConnectionError(f"Unable to connect to Oracle 10g instance at {self.base_url}: {e}")

    def execute_query(self, sql):
        with self._lock:
            if not self.logged_in:
                self._login()

            sql_clean = sql.strip()
            if not sql_clean.endswith(";"):
                sql_clean += ";"

            work_url = f"{self.base_url}/workspace.uix"
            post_data = urllib.parse.urlencode({"script": sql_clean, "event": "execute"}).encode("utf-8")

            try:
                resp = self.opener.open(work_url, data=post_data, timeout=15)
                content = resp.read().decode("utf-8", errors="replace")
            except Exception as e:
                # retry once after relogin
                self._login()
                resp = self.opener.open(work_url, data=post_data, timeout=15)
                content = resp.read().decode("utf-8", errors="replace")

            # Check if session timed out and we got redirected to login
            if "login.uix" in resp.geturl() or ("connectID" in content and "Login" in content):
                self._login()
                resp = self.opener.open(work_url, data=post_data, timeout=15)
                content = resp.read().decode("utf-8", errors="replace")

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

# Convenience instance and helpers
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
    Returns True on success or raises RuntimeError on Oracle error.
    """
    sql_clean = sql.strip()
    if not sql_clean.endswith(";"):
        sql_clean += ";"
    if "commit;" not in sql_clean.lower():
        sql_clean += "\nCOMMIT;"
    db.execute_query(sql_clean)
    return True
