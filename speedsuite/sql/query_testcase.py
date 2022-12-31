import sqlite3
import secrets
import traceback
import pandas as pd

_test_id = ""


class NanoSqlQuery():

    def __init__(self):
        self.open()

    def open(self):
        self.conn = sqlite3.connect('./speedsuite/sql/nano_testcases.db')
        self.cur = self.conn.cursor()

    def query_status_by_testid(self):

        df = pd.read_sql_query(
            '''
            SELECT                 
                tc.start_date,
                test_name,
                step_name,
                CASE conf_count_expected - min(conf_count_all) WHEN 0 THEN 'PASS' ELSE 'FAIL' END as status,
                max(duration_s) as test_duration,
                node_version
            FROM test_suiteinfo ti
            INNER JOIN test_confirmations tc on tc.suite_id =ti.suite_id AND tc.start_date is not null
            GROUP BY test_id, step_name
            ORDER BY tc.start_date ASC
            ''', self.conn)
        print(df.to_string())

    def query_suite_status(self):

        res = self.cur.execute('''
            SELECT min(status) as suite_status from 
                (SELECT                
                    CASE conf_count_expected - min(conf_count_all) WHEN 0 THEN 'PASS' ELSE 'FAIL' END as status                
                FROM test_suiteinfo ti
                INNER JOIN test_confirmations tc on tc.suite_id =ti.suite_id AND tc.start_date is not null
                GROUP BY test_id) as t1
            
            ''')
        #return FAIL if any one testcase failed. Else return PASS
        return res.fetchone()[0]

    def query_failed_testcases_detail(self):

        df = pd.read_sql_query(
            '''
            SELECT 
                test_name,
                step_name,
                tc.start_date,
                node_version, 
                conf_count_expected,
                conf_count_expected - max(conf_count_all) as min_missing_conf,
                conf_count_expected - min(conf_count_all) as max_missing_conf,
                max(duration_s) as test_duration,
                count(NULLIF(conf_p50,0)) as p50_node_count,
                avg(NULLIF(cps_p50,0)) as p50_cps,
                count(NULLIF(conf_p90,0)) as p90_node_count,
                avg(NULLIF(cps_p90,0)) as p90_cps,
                count(NULLIF(conf_p99,0)) as p99_node_count,
                avg(NULLIF(cps_p99,0)) as p99_cps,
                count(NULLIF(conf_p100,0)) as p100_node_count,
                avg(NULLIF(cps_p100,0)) as p100_cps
            FROM test_suiteinfo ti
            INNER JOIN test_confirmations tc on tc.suite_id =ti.suite_id AND tc.start_date is not null
            GROUP BY test_id, step_name
            HAVING max_missing_conf > 0
            ORDER BY tc.start_date ASC
            ''', self.conn)
        print(df.to_string())

    def query_testcases_detail(self):
        df = pd.read_sql_query(
            '''
            SELECT 
                test_name,
                step_name,
                tc.start_date,
                CASE conf_count_expected - min(conf_count_all) WHEN 0 THEN 'PASS' ELSE 'FAIL' END as status,
                node_version, 
                conf_count_expected,
                conf_count_expected - max(conf_count_all) as min_missing_conf,
                conf_count_expected - min(conf_count_all) as max_missing_conf,
                max(duration_s) as test_duration,
                count(NULLIF(conf_p50,0)) as p50_node_count,
                avg(NULLIF(cps_p50,0)) as p50_cps,
                count(NULLIF(conf_p90,0)) as p90_node_count,
                avg(NULLIF(cps_p90,0)) as p90_cps,
                count(NULLIF(conf_p99,0)) as p99_node_count,
                avg(NULLIF(cps_p99,0)) as p99_cps,
                count(NULLIF(conf_p100,0)) as p100_node_count,
                avg(NULLIF(cps_p100,0)) as p100_cps
            FROM test_suiteinfo ti
            INNER JOIN test_confirmations tc on tc.suite_id =ti.suite_id AND tc.start_date is not null
            GROUP BY test_id, step_name
            ORDER BY tc.start_date ASC
            ''', self.conn)
        print(df.to_string())

    def query_cps_100(self):
        df = pd.read_sql_query(
            '''
            SELECT 
                test_name,
                step_name,
                tc.start_date,                
                node_version,
                max(NULLIF(cps_p100,0)) as p100_cps
            FROM test_suiteinfo ti
            INNER JOIN test_confirmations tc on tc.suite_id =ti.suite_id AND tc.start_date is not null
            GROUP BY test_id, step_name
            ORDER BY tc.start_date ASC
            ''', self.conn)
        print(df.to_string())

    def query_cps_p25_to_p90(self):
        df = pd.read_sql_query(
            '''
            SELECT 
                test_name,
                start_date,
                node_version,
                conf_count_all as confirmed_blocks,
                printf('%d.%02d', (block_count_p90 - block_count_p50) / conf_p25_to_p90,10,2) AS cps_p50_to_p90,
                cps_p100
            FROM
                (SELECT
                    test_id,
                    test_name,
                    step_name,
                    tc.start_date,                
                    node_version,
                    conf_p90 - conf_p50 as conf_p25_to_p90,
                    cps_p50 * conf_p50  as block_count_p50,
                    cps_p90 * conf_p90  as block_count_p90,
                    cps_p100,
                    conf_count_all
                FROM test_suiteinfo ti
                INNER JOIN test_confirmations tc on tc.suite_id =ti.suite_id AND tc.start_date is not null
                GROUP BY test_id, step_name
                ORDER BY tc.start_date ASC) as t
             GROUP BY test_id, step_name
             ORDER BY start_date ASC
            ''', self.conn)
        print(df.to_string())

    def query_testcases_all_rows(self):
        df = pd.read_sql_query(
            '''
            SELECT 
            	ti.start_date,
                test_name,
                step_name,
                node_name,
                CASE conf_count_expected - conf_count_all WHEN 0 THEN 'PASS' ELSE 'FAIL' END as status,
                *
            FROM test_suiteinfo ti
            INNER JOIN test_confirmations tc on tc.suite_id =ti.suite_id AND tc.start_date is not null
            ORDER BY ti.start_date ASC
            ''', self.conn)
        print(df.to_string())
