import sqlite3
import secrets
import traceback

_test_id = ""


class NanoSql():

    def __init__(self, suite_id=""):
        self.suite_id = suite_id
        self.script_path = "./speedsuite/sql"
        #print("DEBUG NANOSQL OPENED >>>>>>>>>>", _test_id)
        self.open()
        if _test_id == "":
            self.new_testcase_id()

    def new_testcase_id(self):
        global _test_id
        _test_id = secrets.token_hex(32)
        #print("DEBUG >>>>>>>>>> _test_id", _test_id)
        return _test_id

    def open(self):
        self.con = sqlite3.connect(f'{self.script_path}/nano_testcases.db')
        self.cur = self.con.cursor()
        self.load_schema()

    def load_schema(self):
        res = self.cur.execute(
            "SELECT count(1) FROM sqlite_master WHERE type='table' AND name in ('test_pregen', 'test_publish' , 'test_confirmations', 'test_suiteinfo');"
        )
        if res.fetchone()[0] != 4:
            with open(f"{self.script_path}/easy_schema.sqlite3.sql", "r") as f:
                for query in f.read().split(";"):
                    self.cur.execute(query)

    def insert_pregen_stats(self, params):
        #self.cur.execute(f"INSERT INTO test_pregen(test_id,node_name,start_time,end_time,duration_s,bps) VALUES ({self.test_id}, {node_name}, {start_time},{end_time},{duration_s},{bps})")
        self.insert_sql("test_pregen", params)

    def insert_publish_stats(self, params):  #add sync

        #test_id
        #node_name
        #start_time
        #end_time
        #duration_s
        #bps
        #is_sync
        self.insert_sql("test_publish", params)

    def insert_testcase_stats(self, node_name, env, node_version, testcase,
                              testfunction, start_time, end_time, duration_s,
                              block_count, is_pr, is_publisher, ws_url,
                              rpc_url):
        params = (_test_id, node_name, env, testcase, testfunction, start_time,
                  end_time, duration_s, block_count, is_pr, is_publisher,
                  ws_url, rpc_url, node_version)
        self.cur.execute(
            "INSERT INTO test_cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            params)

        self.con.commit()

    def insert_stats_ws_confirmation(self, params):
        self.insert_sql("test_confirmations", params)

    def insert_suite_info(self, params):
        self.insert_sql("test_suiteinfo", params, add_test_id=False)

    def update_suite_info_end_date(self, params):
        self.cur.execute('update test_suiteinfo set end_date=?', params)

    def insert_confirmation_stats(self, node_name, conf_p50, conf_p75,
                                  conf_p90, conf_p99, conf_p100,
                                  conf_p100_all_blocks, cps_p50, cps_p75,
                                  cps_p90, cps_p99, cps_p100,
                                  cps_p100_all_blocks):

        params = (node_name, conf_p50, conf_p75, conf_p90, conf_p99, conf_p100,
                  conf_p100_all_blocks, cps_p50, cps_p75, cps_p90, cps_p99,
                  cps_p100, cps_p100_all_blocks)
        self.insert_sql("test_confirmations", params)

    def insert_sql(self, table, params, add_test_id=True):
        values = "?" + (",?" * len(params))
        try:
            if add_test_id:
                #print("DEBUG INSERT SQL >>>>>>>>>> ", f"INSERT INTO {table} VALUES (?,{values})", (_test_id,) + params + (self.suite_id,) )
                self.cur.execute(f"INSERT INTO {table} VALUES (?,{values})",
                                 (_test_id, ) + params + (self.suite_id, ))
            else:
                #print("DEBUG INSERT SQL >>>>>>>>>> ", f"INSERT INTO {table} VALUES ({values})", params + (self.suite_id,) )
                self.cur.execute(f"INSERT INTO {table} VALUES ({values})",
                                 params + (self.suite_id, ))
            self.con.commit()
        except:
            print("DEBUG>>>trace insert_sql")
            traceback.print_exc()

    def close(self):
        self.con.close()
