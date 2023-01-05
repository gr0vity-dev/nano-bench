from datetime import datetime
from speedsuite.sql.insert_testcase import NanoSql
import time
from copy import deepcopy
import secrets
from threading import Timer

from nanolocal.common.nl_rpc import NanoRpc


class RepeatedTimer(object):

    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.function = function
        self.interval = interval
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


class StatsLogger():

    env = ""
    test_name = ""
    suite_id = ""

    # def __init__(self): #, testname, step_name, nl_config_path) :
    #     self.testname = testname
    #     self.start_time = datetime.now().strftime('%y-%m-%d %H:%M')
    #     self.timer_start = time.time()
    #     self.step_name = step_name

    # #global stats
    # def __params(self) :
    #     self.node_name = ""
    #     self.env = ""
    #     self.test_name = ""
    #     self.step_name = ""
    #     self.version = ""
    #     self.block_count = 0
    #     self.node_is_pr = None,
    #     self.node_is_publisher = None
    #     self.duration = None
    def __init__(self, node_name="", node_version=""):
        self.node_name = node_name
        self.version = node_version
        self.cps = {
            "cps_10p": 0,
            "cps_25p": 0,
            "cps_50p": 0,
            "cps_75p": 0,
            "cps_90p": 0,
            "cps_99p": 0,
            "cps_100p": 0
        }

        self.conf = {
            "conf_10p": 0,
            "conf_25p": 0,
            "conf_50p": 0,
            "conf_75p": 0,
            "conf_90p": 0,
            "conf_99p": 0,
            "conf_100p": 0
        }

    def new_testsuite(self, env_l, test_name_l):
        global env, test_name, suite_id
        env = env_l
        test_name = test_name_l
        self.start_date = datetime.now().strftime('%y-%m-%d %H:%M:%S')
        suite_id = secrets.token_hex(32)
        self.__insert_into_sql()

    def set_conf_stats(self, conf_np, cps_np, conf_perc, conf_value,
                       expected_count, timer_first_conf):

        if self.conf[conf_np] == 0 and conf_perc >= conf_value:
            self.conf[conf_np] = time.time() - timer_first_conf
            self.cps[cps_np] = (expected_count *
                                (conf_perc / 100)) / self.conf[conf_np]
            self.print_advancement(conf_perc, self.conf[conf_np],
                                   self.cps[cps_np], expected_count)

    def print_advancement(self, conf_perc, duration, cps_np, expected_count):
        #print(f">>>> {round(duration,2)}s for {round(conf_perc,2)}%  @{round(cps_np,2)} cps ")
        print(
            ">>> {:>10} {:>6}% in {:<9}s @{:>8}cps -- {} | expected count: {}".
            format(self.node_name, round(conf_perc, 2), round(duration, 2),
                   round(cps_np, 2), self.version, expected_count))

    # def blockCreateStats_init(self):
    #     self.s_bc = self.BlockCreateStats(datetime.now().strftime('%y-%m-%d %H:%M:%S'))
    # def blockCreateStats_add(self, end_time, bps):
    #     self.s_bc.end_time = end_time
    #     self.s_bc.duration_s = self.s_bc.end_time - self.s_bc.start_time
    #     self.s_bc.bps = bps

    def update_sql_end_date(self):
        end_date = self.end_date = datetime.now().strftime('%y-%m-%d %H:%M:%S')
        NanoSql(suite_id).update_suite_info_end_date((end_date, ))

    def __insert_into_sql(self):
        end_date = self.end_date = datetime.now().strftime('%y-%m-%d %H:%M:%S')
        NanoSql(suite_id).insert_suite_info(
            (env, self.start_date, end_date, test_name))


class BlockCreateStats(StatsLogger):

    def __init__(self, node_name=""):
        self.start_time = time.time()
        self.node_name = node_name

    def set_stats(self, block_count, log_type="sql"):
        self.end_time = time.time()
        self.duration_s = self.end_time - self.start_time
        self.block_count = block_count
        self.bps = block_count / self.duration_s
        if log_type == "sql":
            NanoSql(suite_id).insert_pregen_stats(
                (self.node_name, self.start_time, self.end_time,
                 self.duration_s, self.bps))
        if log_type == "console":
            print(vars(self))


class PublishStats(StatsLogger):

    def __init__(self, nodename=""):
        self.start_date = datetime.now().strftime('%y-%m-%d %H:%M:%S')
        self.start_time = time.time()
        self.node_is_publisher = True
        self.node_name = nodename

    def set_stats(self,
                  block_count,
                  sync,
                  log_type="sql"):  #TODO add sync to sql
        self.end_time = time.time()
        self.duration_s = self.end_time - self.start_time
        self.block_count = block_count
        self.bps = block_count / self.duration_s
        if log_type == "sql":
            NanoSql(suite_id).insert_publish_stats(
                (self.node_name, self.start_time, self.end_time,
                 self.duration_s, self.bps, sync))
        if log_type == "console":
            print(vars(self))


class WebsocketConfirmationStats(StatsLogger):

    def __init__(self, node_name, node_version, step_name):
        super().__init__(node_name, node_version)
        self.stats_is_logged = False

        self.expected_hashes = []
        self.remaining_hashes = []
        self.confirmed_hashes_in_expected = []
        self.confirmed_hashes_out_expected = []

        self.expected_count = 0

        self.start_date = datetime.now().strftime('%y-%m-%d %H:%M:%S')
        self.start_timer = time.time()
        self.duration_first_conf = 0
        self.timer_first_conf = None
        self.end_date = None
        self.duration_s = 0

        #self.bps = 0
        #self.block_count = 0
        self.node_is_publisher = None
        self.node_name = node_name
        self.version = node_version
        self.step_name = step_name
        self.conf_count_all = 0
        self.conf_count_in_expected = 0

        self.conf_100p_all = 0
        self.cps_100p_all = 0

    def set_expected_hashes(self, hash_list):
        hash_copy = []
        if any(isinstance(i, list) for i in hash_list):  #nested list :
            for i in range(0, len(hash_list)):
                self.expected_count = self.expected_count + len(hash_list[i])
                hash_copy.extend(deepcopy(hash_list[i]))
        else:
            hash_copy = deepcopy(hash_list)
            self.expected_count = len(hash_copy)

        self.expected_hashes = hash_copy
        self.remaining_hashes = deepcopy(hash_copy)

    def inc_confirmation_counter(self):
        self.conf_count_all = self.conf_count_all + 1

    def receive_hash(self, hash):
        self.update_hash_lists(hash)
        self.update_confirmation_count()

    def update_hash_lists(self, hash):
        if hash in self.expected_hashes:
            self.remaining_hashes.remove(hash)
            self.confirmed_hashes_in_expected.append(hash)
            if self.timer_first_conf == None:
                self.timer_first_conf = time.time()
                self.duration_first_conf = round(time.time() -
                                                 self.start_timer)
        else:
            self.confirmed_hashes_out_expected.append(hash)

    def update_confirmation_count(self):
        #conf_perc =(confirmed / expected) * 100
        confirmed_count = self.get_confirmed_hashes_count_expected()
        conf_count_all = self.get_confirmed_hashes_count_all()
        conf_perc = (confirmed_count / self.expected_count) * 100

        super().set_conf_stats("conf_10p", "cps_10p", conf_perc, 10,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_25p", "cps_25p", conf_perc, 25,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_50p", "cps_50p", conf_perc, 50,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_75p", "cps_75p", conf_perc, 75,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_90p", "cps_90p", conf_perc, 90,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_99p", "cps_99p", conf_perc, 99,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_100p", "cps_100p", conf_perc, 100,
                               self.expected_count, self.timer_first_conf)

        if self.conf_100p_all == 0 and conf_count_all >= self.expected_count:
            self.conf_100p_all = time.time() - self.timer_first_conf
            self.cps_100p_all = self.expected_count / self.conf_100p_all
            super().print_advancement(conf_perc, self.conf_100p_all,
                                      self.cps_100p_all, self.expected_count)

    def get_remaining_hashes(self):
        return self.remaining_hashes

    def get_remaining_hashes_count(self):
        count = len(self.remaining_hashes)
        return count

    def get_confirmed_hashes_count_expected(self):
        return len(self.confirmed_hashes_in_expected)

    def get_confirmed_hashes_count_all(self):
        return len(self.confirmed_hashes_in_expected) + len(
            self.confirmed_hashes_out_expected)

    def log_stats(self, log_type="sql"):
        if self.stats_is_logged: return

        self.end_date = datetime.now().strftime('%y-%m-%d %H:%M:%S')
        self.duration_s = time.time() - self.start_timer

        if log_type == "sql":
            #print([{key : value} if not isinstance(value, list) else {key : f'length={len(value)}'} for key,value in vars(self).items()])
            self.insert_into_sql()
            self.stats_is_logged = True
        if log_type == "console":
            print([{
                key: value
            } if not isinstance(value, list) else {
                key: f'length={len(value)}'
            } for key, value in vars(self).items()])
            self.stats_is_logged = True

    def insert_into_sql(self):
        NanoSql(suite_id).insert_stats_ws_confirmation(
            (self.expected_count, self.start_date, self.duration_first_conf,
             self.end_date, self.duration_s, self.conf["conf_10p"],
             self.conf["conf_25p"], self.conf["conf_50p"],
             self.conf["conf_75p"], self.conf["conf_90p"],
             self.conf["conf_99p"], self.conf["conf_100p"],
             self.cps["cps_10p"], self.cps["cps_25p"], self.cps["cps_50p"],
             self.cps["cps_75p"], self.cps["cps_90p"], self.cps["cps_99p"],
             self.cps["cps_100p"], self.node_is_publisher, self.node_name,
             self.version, self.conf_count_all, self.conf_count_in_expected,
             self.conf_100p_all, self.cps_100p_all, self.step_name))


class BlockCountConfirmationStats(StatsLogger):

    def __init__(self,
                 nano_rpc: NanoRpc,
                 node_name,
                 node_version,
                 expected_count,
                 pass_count,
                 step_name,
                 timeout=3600):

        super().__init__(node_name, node_version)
        # super().node_name = node_name
        # super().version = node_version

        self.log_error_on_block_count = True
        self.stats_is_logged = False
        self.nano_rpc = nano_rpc

        self.expected_hashes = []
        self.remaining_hashes = []
        self.confirmed_hashes_in_expected = []
        self.confirmed_hashes_out_expected = []

        self.expected_count = expected_count
        self.pass_count = pass_count
        self.step_name = step_name
        self.timeout = timeout
        self.is_timeout = False

        self.start_date = datetime.now().strftime('%y-%m-%d %H:%M:%S')
        self.start_timer = time.time()
        self.duration_first_conf = 0
        self.timer_first_conf = time.time()
        self.end_date = None
        self.duration_s = 0

        #self.bps = 0
        #self.block_count = 0
        self.node_is_publisher = None
        self.conf_count_all = 0
        self.conf_count_in_expected = 0

    def log_block_count(self):
        try:
            if time.time() - self.start_timer >= self.timeout:
                self.rt.stop()
                self.log_stats()
                self.is_timeout = True

            block_count = self.nano_rpc.block_count()
            cemented_count = int(block_count["cemented"])
            self.update(cemented_count)
            self.log_error_on_block_count = True
        except Exception as error_msg:
            if self.log_error_on_block_count:
                print("Node is restarting...")
                self.log_error_on_block_count = False
            else:
                print("Exception raised for [log_block_count]", str(error_msg))

    def set_confirmation_counter(self, confirmed_count) -> None:
        self.conf_count_all = confirmed_count

    def start(self, repeat_s=1):
        self.rt = RepeatedTimer(repeat_s, self.log_block_count)  #
        self.rt.start()

    def is_confirmed_or_timeout(self):
        if self.is_fully_confirmed(): return True
        if self.is_timeout: return True
        return False

    def is_fully_confirmed(self, log_on_confirmed=True):
        is_confirmed = (self.conf_count_all >= self.expected_count)
        if is_confirmed: self.rt.stop()
        if is_confirmed and log_on_confirmed: self.log_stats()
        return is_confirmed

    def update(self, confirmed_count) -> bool:
        confirmed_count = self.expected_count - (self.pass_count -
                                                 confirmed_count)

        self.set_confirmation_counter(confirmed_count)
        self.update_confirmation_count(confirmed_count)

    def update_confirmation_count(self, confirmed_count) -> None:
        #conf_perc =(confirmed / expected) * 100
        conf_perc = (confirmed_count / self.expected_count) * 100
        print(">>>>DEBUG,", conf_perc, confirmed_count, self.expected_count,
              self.pass_count)
        super().set_conf_stats("conf_10p", "cps_10p", conf_perc, 10,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_25p", "cps_25p", conf_perc, 25,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_50p", "cps_50p", conf_perc, 50,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_75p", "cps_75p", conf_perc, 75,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_90p", "cps_90p", conf_perc, 90,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_99p", "cps_99p", conf_perc, 99,
                               self.expected_count, self.timer_first_conf)
        super().set_conf_stats("conf_100p", "cps_100p", conf_perc, 100,
                               self.expected_count, self.timer_first_conf)

    def get_remaining_hashes_count(self):
        count = self.expected_count - self.conf_count_all
        return count

    def get_confirmed_hashes_count_expected(self):
        return self.conf_count_all

    def get_confirmed_hashes_count_all(self):
        return self.conf_count_all

    def log_stats(self, log_type="sql"):
        if self.stats_is_logged: return

        self.end_date = datetime.now().strftime('%y-%m-%d %H:%M:%S')
        self.duration_s = time.time() - self.start_timer

        if log_type == "sql":
            #print([{key : value} if not isinstance(value, list) else {key : f'length={len(value)}'} for key,value in vars(self).items()])
            self.insert_into_sql()
            self.stats_is_logged = True
        if log_type == "console":
            print([{
                key: value
            } if not isinstance(value, list) else {
                key: f'length={len(value)}'
            } for key, value in vars(self).items()])
            self.stats_is_logged = True

    def insert_into_sql(self):
        NanoSql(suite_id).insert_stats_ws_confirmation(
            (self.expected_count, self.start_date, self.duration_first_conf,
             self.end_date, self.duration_s, self.conf["conf_10p"],
             self.conf["conf_25p"], self.conf["conf_50p"],
             self.conf["conf_75p"], self.conf["conf_90p"],
             self.conf["conf_99p"], self.conf["conf_100p"],
             self.cps["cps_10p"], self.cps["cps_25p"], self.cps["cps_50p"],
             self.cps["cps_75p"], self.cps["cps_90p"], self.cps["cps_99p"],
             self.cps["cps_100p"], self.node_is_publisher, self.node_name,
             self.version, self.conf_count_all, self.conf_count_in_expected,
             self.conf["conf_100p"], self.cps["cps_100p"], self.step_name))


class WebsocketVoteStats(StatsLogger):

    def __init__(self):
        self.start_time = datetime.now().strftime('%y-%m-%d %H:%M:%S')
        self.end_time = ""
        self.duration_s = ""
        self.bps = ""
        self.vote_count = 0
        self.node_is_publisher = None
        node_name = ""
        version = ""
