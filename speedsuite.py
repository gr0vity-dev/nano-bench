#!./venv_nanolocal/bin/python

from speedsuite.common.simple_ws import SimpleWs
from speedsuite.common.stats_logger import BlockCreateStats, PublishStats, StatsLogger, BlockCountConfirmationStats
from speedsuite.sql.insert_testcase import NanoSql
from speedsuite.common.error_messages import raise_value_error, raise_exception
from nanolocal.common.nl_rpc import NanoRpc
from nanolocal.common.nl_parse_config import ConfigParser, ConfigReadWrite
from nanolocal.common.nl_block_tools import BlockAsserts, BlockReadWrite
from submodules.xnolib.peercrawler import get_connected_socket_endpoint, message_header, block_state, testctx, livectx, betactx, message_type_enum, network_id, message_type, get_peers_from_service, random, block_type_enum
from submodules.xnolib.msg_handshake import node_handshake_id

from signal import signal, SIGINT
from subprocess import call
from datetime import datetime
from math import ceil
from itertools import islice

import os
import re
import time
import asyncio
import argparse
import threading
import traceback
import collections, functools, operator

_ENV = None
_SUITE_CONFIG = {}
_CURRENT_STEP = ""
_SHELL_ENV_VARIABLES = {}
_FILE_PATH = {"building_blocks": "./speedsuite/testcases/building_blocks/"}
_BACKGROUND_THREADS = []  #shared variable across all NanoRunner Instances
_WEBSOCKET_CLIENTS = {}
_PREGEN_BLOCKS = []
_loop = None


def start_async_loop():
    global _loop
    _loop = asyncio.new_event_loop()
    threading.Thread(target=_loop.run_forever).start()


# Submits awaitable to the event loop, but *doesn't* wait for it to
# complete. Returns a concurrent.futures.Future which *may* be used to
# wait for and retrieve the result (or exception, if one was raised)
def submit_async(awaitable):
    return asyncio.run_coroutine_threadsafe(awaitable, _loop)


def stop_async_loop():
    _loop.call_soon_threadsafe(_loop.stop)


def run_threaded(job_func, *args, **kwargs):
    job_thread = threading.Thread(target=job_func, *args, **kwargs)
    job_thread.start()
    return job_thread


def threads_join_step():
    for t in _BACKGROUND_THREADS:
        if t["thread"] is None: continue
        elif "join_step" in t and t["join_step"]:
            t["thread"].join()


def threads_join_all():
    for t in _BACKGROUND_THREADS:
        if t["thread"] is None: continue
        elif "join_end" in t and t["join_end"]:
            t["thread"].join()

    ws: SimpleWs
    for ws in _WEBSOCKET_CLIENTS.values():
        ws.terminate()

    _BACKGROUND_THREADS.clear()
    _WEBSOCKET_CLIENTS.clear()


class NanoRunner():

    def __init__(self,
                 env,
                 step_name,
                 step_config,
                 bb_json="default.json") -> None:

        # if _ENV == "nanolocal":
        #     self.p = PreGenLedger(_ENV,
        #                           ConfigParser().get_nodes_rpc()[0], True)
        # else:
        #     self.p = PreGenLedger(_ENV, _SHELL_ENV_VARIABLES["RPC_URL"], True)

        self.stats = StatsLogger()
        self.env = env
        self.step_name = step_name
        self.step_config = self.load_building_block(step_name, step_config,
                                                    bb_json)
        print("===========", step_name, "===============")
        self.check_allowed_teststep_values("function",
                                           self.step_config.get("function"))

    def run(self):
        if self.skip_step():
            return
        elif self.step_config["function"] == "assert":
            self.rpc_config()
        elif self.step_config["function"] == "publish":
            self.publish()
        elif self.step_config["function"] == "load_blocks":
            self.load_blocks_into_memory()
        elif self.step_config["function"] == "log_progress":
            self.log_progress()
        elif self.step_config["function"] == "run_commands":
            prepare_shell_commands(self.step_config)
            self.run_commands()
        threads_join_step()

    def append_background_threds(self, thread, join_step=False, join_end=True):
        _BACKGROUND_THREADS.append({
            "join_step": join_step,
            "join_end": join_end,
            "thread": thread
        })

    def run_commands(self):
        for command in self.step_config['action']:
            self.run_shell_command(command)

    def run_shell_command(self, command):
        run_shell_command(command)

    def skip_step(self):
        if "skip" in self.step_config and self.step_config["skip"] == True:
            print("===========", "SKIPPED", self.step_name, "===============")
            return True
        return False

    def load_building_block(self, step_name, step_config, bb_json):
        if _ENV != "nanolocal": step_config
        building_block_parts = step_name.split(".")
        #replace
        if building_block_parts[0] == "_bb":
            step_config.update(_SHELL_ENV_VARIABLES)
            all_building_block = ConfigReadWrite().read_json(
                f"{_FILE_PATH['building_blocks']}{bb_json}")

            current_building_block = all_building_block[
                building_block_parts[1]]
            if building_block_parts[1] in all_building_block:
                if "shell_vars" in current_building_block:
                    for shell_var in current_building_block["shell_vars"]:
                        if shell_var in step_config.keys():
                            for i, command in enumerate(
                                    current_building_block["action"]):
                                current_building_block["action"][
                                    i] = command.replace(
                                        f"${shell_var}",
                                        step_config[shell_var])
                        else:
                            raise_value_error("undefined_shell_var", shell_var)

                return all_building_block[building_block_parts[1]]
            else:
                raise_value_error(
                    "missing_build_block", building_block_parts[1],
                    "./speedsuite/testcases/nanolocal/building_blocks.json")

        elif building_block_parts[0] == "_func":
            return {"function": building_block_parts[1], "params": step_config}

        return step_config

    def rpc_config(self):
        params = self.get_params()
        if params.get("assert") == "block_count_eq":
            BlockAsserts().assert_increasing_block_count(
                params.get("block_count"))
        elif params.get("assert") == "block_count_ge":
            pass

    def check_allowed_teststep_values(self, key, value):
        if self.skip_step():
            return True

        test_functions = [
            "blocks_create",
            "blocks_load",
            "publish",
            "run_commands",
            "log_progress",
            "load_blocks",
            "create_publish",
        ]

        blocks_create = [
            "account_splitter", "bucket_funding",
            "bucket_funding_multi_origin", "spam_send_receive",
            "spam_self_send_receive", "change_spam", "multi_spam",
            "bucket_change_rounds", "spam_change_wait_conf",
            "spam_send_wait_conf_random", "spam_send_receive_random_tangle",
            "spam_ping_pong", "forks"
        ]

        run_conditional = [None, "always", "once_per_docker_version", "once"]

        if key == "function":
            if value in test_functions: return True
        if key == "blocks_create":
            if value in blocks_create: return True
        if key == "run_conditional":
            if value in run_conditional: return True

        raise_value_error("misconfig", value, key)

    def publish_conditional(self, blocks, params):
        if params["publisher"]["node"] == "xnolib":
            self.xnolib_publish_threaded(blocks, params)
        else:
            self.rpc_publish_threded(blocks, params)

    def xnolib_publish_threaded(self, blocks, params):
        params = {
            "peers": params["publisher"].get("peers", None),
            "shuffle": params["publisher"].get("shuffle", False),
            "reverse": params["publisher"].get("reverse", False),
            "split": params["publisher"].get("split"),
            "bps": params.get("bps", 1000)
        }
        thread = run_threaded(self.xnolib_publish,
                              args=[blocks["b"]],
                              kwargs={"params": params})

        self.append_background_threds(thread)

    def xnolib_publish(self, block_lists, params={}):
        sp = SocketPublish(params.get("peers", None), params["bps"])
        messages = sp.flatten_messages(block_lists)
        sliced_msg = sp.prepare_message_sliced(messages, params)
        stats = PublishStats("xnolib")
        sp.publish_all(sliced_msg)
        stats.set_stats(len(messages), True)

    def prepare_publish_commands(self, blocks, tps=125):
        publish_commands = []
        if any(isinstance(i, list) for i in blocks):  #nested list :
            for i in range(0, len(blocks)):
                publish_commands.append(
                    self.get_publish_commands_subsets(blocks[i], tps))
        else:
            publish_commands.append(
                self.get_publish_commands_subsets(blocks, tps))
        return publish_commands

    def get_publish_commands_subsets(self, blocks, tps=125):
        blocks_to_publish_count = len(blocks)
        subsets = []
        for i in range(0, ceil(blocks_to_publish_count / tps)):
            blocks_subset = list(islice(blocks, i * tps, i * tps + tps))
            publish_commands = [{
                "action": "process",
                "json_block": "true",
                "subtype": block["subtype"],
                "block": block
            } for block in blocks_subset]
            subsets.append(publish_commands)
        return subsets

    def rpc_publish(self,
                    rpc_url,
                    blocks,
                    bps=125,
                    sync=False,
                    assert_block_count=False,
                    name=""):

        ba = BlockAsserts(rpc_url)
        block_count = 0
        publish_commands = self.prepare_publish_commands(blocks, bps)
        stats = PublishStats(name)
        for i in range(0, len(publish_commands)):
            ba.assert_publish_commands(publish_commands[i],
                                       sync=sync,
                                       bps=bps,
                                       assert_block_count=assert_block_count)
            block_count = block_count + sum(
                [len(x) for x in publish_commands[i]])

        stats.set_stats(block_count, sync)

    def rpc_publish_threded(self, blocks, params):

        if _ENV == "nanolocal":
            rpc = ConfigParser().get_node_rpc(params["publisher"]["node"])
        else:
            rpc = _SUITE_CONFIG["rpc_url"]

        thread = run_threaded(self.rpc_publish,
                              args=[rpc, blocks["b"]],
                              kwargs={
                                  "assert_block_count":
                                  params["publisher"].get("assert_count"),
                                  "bps":
                                  params.get("bps"),
                                  "sync":
                                  params.get("publish_sync"),
                                  "name":
                                  params.get("publisher").get("name")
                              })
        self.append_background_threds(thread)

    def load_blocks_into_memory(self):
        global _PREGEN_BLOCKS
        params = self.get_params()
        _PREGEN_BLOCKS = self.get_blocks_from_disk(params)

    def log_progress(self):
        params = self.get_params()
        if not params.get("blocks_from_memory", False):
            self.load_blocks_into_memory()
        blocks = _PREGEN_BLOCKS

        self.attach_progress_watcher(blocks)
        return blocks, params

    def attach_progress_watcher(self, blocks):
        ws_conf = self.set_defaults_watcher("ws_conf")
        self.get_confirmation_stats_from_ws(ws_conf, blocks["h"])
        self.get_confirmation_stats_from_rpc(
            len(self.flatten_blocks(blocks["h"])))

    def create_publish(self):
        params = self.get_params()
        self.get_confirmation_stats_from_rpc(2 * params["block_count"])
        self.create_publish_threaded(params)

    def publish(self):
        blocks, params = self.log_progress()
        self.publish_conditional(blocks, params)

    def set_defaults_watcher(self, watcher):
        if watcher not in self.step_config["params"]: return
        confp = ConfigParser()
        watcher_config = {}
        self.step_config["params"][watcher].setdefault("join_step", False)
        self.step_config["params"][watcher].setdefault("join_end", False)
        self.step_config["params"][watcher]["urls"] = []
        self.step_config["params"][watcher].setdefault(
            "nodes",
            confp.get_nodes_name()[0])

        for node_name in confp.get_nodes_name():
            if node_name in self.step_config["params"][watcher]["nodes"]:
                ws_config = {}
                node_config = confp.get_node_config(node_name)
                for key, value in node_config.items():
                    if key in ("rpc_url", "ws_url", "name", "account",
                               "is_pr"):
                        ws_config[key] = value
                self.step_config["params"][watcher]["urls"].append(ws_config)

        return self.step_config["params"][watcher]

    def get_params(self):
        self.step_config.setdefault("params", {})
        return self.step_config["params"]

    def get_path(self):
        return {
            "saved_blocks": f"speedsuite/testcases/{_ENV}/saved_blocks/",
            "saved_ledgers": f"speedsuite/testcases/{_ENV}/saved_ledgers/",
            "configs": f"speedsuite/testcases/{_ENV}/configs/",
        }

    def flatten_blocks(self, hash_list):
        hash_copy = []
        if any(isinstance(i, list) for i in hash_list):  #nested list :
            for i in range(0, len(hash_list)):
                hash_copy.extend(hash_list[i])
        else:
            hash_copy = hash_list
            self.expected_count = len(hash_copy)

        return hash_copy

    def get_blocks_from_disk(self, params: dict) -> list:
        # mandatory params: blocks_path
        #  optional params: start_round, end_round, subset
        all_blocks = BlockReadWrite().read_blocks_from_disk(
            self.get_path()["saved_blocks"] + params["blocks_path"])

        params.setdefault("start_round", 0)
        params.setdefault("end_round", len(all_blocks["h"]))
        params.setdefault("subset", {})
        params["subset"].setdefault("start_index", 0)
        #include all blocks in current 'subset' by default.
        params["subset"].setdefault("end_index", max(map(len,
                                                         all_blocks["h"])))

        subset_start_index = params["subset"]["start_index"]
        subset_end_index = params["subset"]["end_index"]

        blocks = {}
        blocks['b'] = [
            x[subset_start_index:subset_end_index]
            for x in all_blocks['b'][params["start_round"]:params["end_round"]]
        ]
        blocks['h'] = [
            x[subset_start_index:subset_end_index]
            for x in all_blocks['h'][params["start_round"]:params["end_round"]]
        ]
        print(">>>DEBUG flatten blocks", len(blocks))
        return blocks

    def get_node_version(self, nano_rpc):
        version_rpc_call = nano_rpc.version()
        node_version = f'{version_rpc_call["node_vendor"]} {version_rpc_call["build_info"].split(" ")[0]}'[
            0:20]
        return node_version

    def get_confirmation_stats_from_ws(self, ws_params, block_hashes):
        global _WEBSOCKET_CLIENTS
        if ws_params is not None:
            for url in ws_params["urls"]:
                if "enable" in url and not url["enable"]: continue
                ws = SimpleWs(url["ws_url"],
                              url["name"],
                              self.get_node_version(NanoRpc(url["rpc_url"])),
                              ws_topics=["confirmation"],
                              current_step=_CURRENT_STEP)
                ws.stats_conf.set_expected_hashes(block_hashes)
                _WEBSOCKET_CLIENTS[url["ws_url"]] = ws
                thread = run_threaded(
                    self.ws_report_progress,
                    args=[url["ws_url"]],
                    kwargs={"timeout_s": ws_params.get("timeout")})

                self.append_background_threds(
                    thread,
                    join_step=ws_params.get("join_step"),
                    join_end=ws_params.get("join_end"))

    def get_confirmation_stats_from_rpc(self, block_count):
        rpc_conf = self.set_defaults_watcher("rpc_conf")
        if rpc_conf is not None:
            loggers = []
            for el in rpc_conf["urls"]:
                nano_rpc = NanoRpc(el["rpc_url"])
                node_version = self.get_node_version(nano_rpc)
                current_cemented = int(nano_rpc.block_count()["cemented"])
                logger = BlockCountConfirmationStats(
                    nano_rpc, el["name"], node_version, block_count,
                    current_cemented + block_count, _CURRENT_STEP,
                    rpc_conf["timeout"])
                logger.start()
                loggers.append(logger)

            logger: BlockCountConfirmationStats
            for logger in loggers:
                thread = run_threaded(
                    self.rpc_report_progress,
                    args=[logger],
                    kwargs={"timeout_s": rpc_conf["timeout"]})

                self.append_background_threds(
                    thread,
                    join_step=rpc_conf.get("join_step", True),
                    join_end=rpc_conf.get("join_end", False))

    def ws_report_progress(self, ws_url, timeout_s=3600):
        start_time = time.time()
        ws: SimpleWs = _WEBSOCKET_CLIENTS[ws_url]
        while ws.stats_conf.get_remaining_hashes_count() > 0:
            if time.time() - start_time > timeout_s or ws.is_closed:
                break
            time.sleep(1)
        ws.terminate()

    def rpc_report_progress(self,
                            logger: BlockCountConfirmationStats,
                            timeout_s=3600):
        start_time = time.time()
        while not logger.is_confirmed_or_timeout():
            if time.time() - start_time > timeout_s: break
            time.sleep(0.5)


class SocketPublish():

    def __init__(self, peers, bps):
        self.bps = bps
        self.sockets, self.hdr = self.__set_sockets_handshake(peers)
        self.is_split = False
        self.is_reverse = False
        self.is_shuffle = False

    def handshake_peer(self, peeraddr, peerport, ctx):
        try:
            print('Connecting to [%s]:%s' % (peeraddr, peerport))
            s = get_connected_socket_endpoint(peeraddr, peerport)
            signing_key, verifying_key = node_handshake_id.keypair()
            node_handshake_id.perform_handshake_exchange(
                ctx, s, signing_key, verifying_key)
            return s
        except Exception as e:
            print(str(e))
            pass

    class msg_publish:

        def __init__(self, hdr, block):
            assert (isinstance(hdr, message_header))
            self.hdr = hdr
            self.block = block

        def serialise(self):
            data = self.hdr.serialise_header()
            data += self.block.serialise(False)
            return data

        def __str__(self):
            return str(self.hdr) + "\n" + str(self.block)

    def get_xnolib_context(self, peers=None):
        if _ENV == "nanolocal":
            ctx = ConfigParser().get_xnolib_localctx()
            ctx["net_id"] = network_id(ord('X'))

        elif _ENV == "test":
            ctx = testctx
        elif _ENV == "beta":
            ctx = betactx
        elif _ENV == "live":
            ctx = livectx

        if peers is not None:  #chose a single peer , if enabled in config file
            for peer in ctx["peers"].copy():
                if peer not in peers: ctx["peers"].pop(peer, None)
        return ctx

    def __set_sockets_handshake(self, peers):
        ctx = self.get_xnolib_context(peers=peers)
        msgtype = message_type_enum.publish
        hdr = message_header(ctx['net_id'], [18, 18, 18],
                             message_type(msgtype), 0)
        hdr.set_block_type(block_type_enum.state)
        all_peers = get_peers_from_service(ctx)
        sockets = []
        #Handshake with all voting peers
        for peer in all_peers:
            s = self.handshake_peer(str(peer.ip), peer.port, ctx)
            if s is not None:
                sockets.append({
                    "socket": s,
                    "peer": str(peer.ip) + ":" + str(peer.port)
                })
        return sockets, hdr

    def flatten_messages(self, block_lists):
        messages = []
        block_count = 0
        for block_list in block_lists:
            block_count = block_count + len(block_list)
            publish_msg = [
                self.msg_publish(self.hdr, block_state.parse_from_json(block))
                for block in block_list
            ]
            messages.extend(publish_msg)
        return messages

    def split_list(self, list_a, n):
        k, m = divmod(len(list_a), n)
        return (list_a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)]
                for i in range(n))

    def prepare_message_sliced(self, messages, params):

        if params.get("reverse", False):
            messages = messages[::-1]
            self.is_reverse = True
        if params.get("shuffle", False):
            random.shuffle(messages)
            self.is_shuffle = True
        if params.get("split", False):
            #split messages in a list of N equal parts
            message_list = list(self.split_list(messages, len(self.sockets)))
            self.is_split = True
        else:
            message_list = [messages]

        sliced_msg = []
        for messages in message_list:
            current_sublist = []
            for message in messages:
                current_sublist.append(message)
                if len(current_sublist) == self.bps:
                    sliced_msg.append(current_sublist)
                    current_sublist = []
            if current_sublist != []:
                sliced_msg.append(current_sublist)
        return sliced_msg

    def get_sleep_duration(self, iteration, start_time, interval, msg_len):
        return min(
            1,
            max(
                0, start_time + (iteration + 1) * interval - time.time() +
                ((msg_len - self.bps) / self.bps)))

    def publish_all(self, sliced_msg):
        start_time = time.time()
        interval = 1
        socket_errors = []

        if self.is_split:
            i = 0
            for messages in sliced_msg:
                msg_index = i % len(self.sockets)
                socket_errors.append(
                    self.exec_parallel_publish_single_socket(
                        messages=messages, s=self.sockets[msg_index]))
                sleep_duration = self.get_sleep_duration(
                    i, start_time, interval / len(self.sockets), len(messages))
                time.sleep(sleep_duration)
                i = i + 1

        else:
            for i, messages in enumerate(sliced_msg):
                for socket in self.sockets:
                    socket_errors.append(
                        self.exec_parallel_publish_single_socket(
                            messages=messages, s=socket))

                sleep_duration = self.get_sleep_duration(
                    i, start_time, interval, len(messages))
                time.sleep(sleep_duration)

        socket_error_sum = dict(
            functools.reduce(operator.add,
                             map(collections.Counter, socket_errors)))
        print(datetime.now(), ">>>>>>DEBUG socket_errors", socket_error_sum)

    def exec_parallel_publish(self, messages=None, s=None):
        res = {}
        submit_async(self.publish(messages, s, results=res))
        return res

    def inc_counter(self, key, json):
        if key not in json:
            json[key] = 0
        json[key] = json[key] + 1

    def recvall(self, sock, size):
        received_chunks = []
        buf_size = 4096
        remaining = size
        while remaining > 0:
            received = sock.recv(min(remaining, buf_size))
            if not received:
                raise_exception("eof")
            received_chunks.append(received)
            remaining -= len(received)
        return b''.join(received_chunks)

    def exec_parallel_publish_single_socket(self, messages=None, s=None):
        res = {}
        submit_async(self.publish_single_socket(messages, s, results=res))
        return res

    async def publish_single_socket(self, messages, s, results={}):

        # for socket in s:
        #     for msg in messages:
        #         socket["socket"].sendall(msg.serialise())

        #semaphore = asyncio.Semaphore(50)
        #print(50)
        counter = {}

        async def do_req(msg, s, counter):
            try:
                counter.setdefault(f'{s["peer"]}', 0)
                counter[f'{s["peer"]}'] = counter[f'{s["peer"]}'] + 1
                s["socket"].sendall(msg.serialise())
                #self.recvall(s["socket"], 1)
            except Exception as e:
                print(s["peer"], str(e))
                self.inc_counter(s["peer"], results)

        await asyncio.gather(*(do_req(el, s, counter) for el in messages))

    async def publish(self, messages, s, results={}):

        # for socket in s:
        #     for msg in messages:
        #         socket["socket"].sendall(msg.serialise())

        #semaphore = asyncio.Semaphore(50)
        #print(50)
        counter = {}

        async def do_req(msg, s, counter):
            #async with semaphore:
            for count, socket in enumerate(s):
                try:
                    counter.setdefault(f"s{count}", 0)
                    counter[f"s{count}"] = counter[f"s{count}"] + 1
                    socket["socket"].sendall(msg.serialise())
                    self.recvall(socket["socket"], 1)
                except Exception as e:
                    print(socket["peer"], str(e))
                    self.inc_counter(socket["peer"], results)

        await asyncio.gather(*(do_req(el, s, counter) for el in messages))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', help='string')
    parser.add_argument('--runid', help='string')
    return parser.parse_args()


def run_shell_command(command):
    status = call(command, shell=True)
    print(command, "| status:", status)
    if status != 0:
        raise_exception("command_failed", command, status)


# #DEBUG : put def parse_args() into comment and set the command you wish to run
# def parse_args() :
#    return argClass
# class argClass :
#    testname = "multi_spam_change_100k"
#    actions = ["pregen", "publish"]


def validate_config():
    global _ENV
    _ENV = _SUITE_CONFIG["env"]

    _SUITE_CONFIG.setdefault("bb_path", "default.json")
    _SUITE_CONFIG.setdefault("runs_per_version", 1)

    if _ENV == "no_validate":
        return
    if _ENV == "nanolocal":
        _SUITE_CONFIG.setdefault("docker_versions", "empty")
    elif _ENV == "test":
        if "rpc_url" not in _SUITE_CONFIG:
            raise_value_error("rpc_url_not_found")
        _SHELL_ENV_VARIABLES["RPC_URL"] = _SUITE_CONFIG["rpc_url"]
    elif _ENV == "beta":
        if "rpc_url" not in _SUITE_CONFIG:
            raise_value_error("rpc_url_not_found")
        _SHELL_ENV_VARIABLES["RPC_URL"] = _SUITE_CONFIG["rpc_url"]
    elif _ENV == "live":
        if "rpc_url" not in _SUITE_CONFIG:
            raise_value_error("rpc_url_not_found")
        _SHELL_ENV_VARIABLES["RPC_URL"] = _SUITE_CONFIG["rpc_url"]
    else:
        raise_value_error("invalid_env")


def prepare_shell_commands(testcase):
    global _SHELL_ENV_VARIABLES
    for i, command in enumerate(testcase['action']):
        #export all shell vars into a global application variable
        pattern = "export ([\w\d\s]+)=([\S]+)"
        for match_regex in re.findall(pattern, command):
            _SHELL_ENV_VARIABLES[match_regex[0]] = match_regex[1]

        #Replace $VAR with exported value
        for shell_var, value in _SHELL_ENV_VARIABLES.items():
            if f"${shell_var}" in command:
                testcase['action'][i] = command.replace(f"${shell_var}", value)


def load_testcase_config():
    testcase_config = _SUITE_CONFIG["testsuite"]
    #testcase_config[list(testcase_config.keys())[0]].setdefault("params", {})

    return testcase_config


def inc_current_repeat(step_config: dict, i):

    step_config.setdefault("params", {})
    step_config["params"]["current_repeat"] = i


def get_docker_versions(config):
    return [
        version for version in config["docker_versions"]
        for _ in range(config["runs_per_version"])
    ]


def init_runs():
    total_runs = _SUITE_CONFIG["runs_per_version"] * len(
        _SUITE_CONFIG["docker_versions"])
    return total_runs, 0


def set_global_shell_variables(current_run):
    _SHELL_ENV_VARIABLES["DOCKER_TAG"] = get_docker_versions(
        _SUITE_CONFIG)[current_run]
    _SHELL_ENV_VARIABLES["TEST_NAME"] = _SUITE_CONFIG["testname"]


def init_testcase(current_run):
    NanoSql().new_testcase_id()
    start_async_loop()
    set_global_shell_variables(current_run)


def cleanup_testcase():
    threads_join_all()
    stop_async_loop()
    #reset all in memory blocks for the next testrun
    NanoRpc("dummy_url").clear_in_mem_account_info()
    time.sleep(_SUITE_CONFIG.get("iterations_wait_s", 10))


def run_steps(testcase_config):
    global _CURRENT_STEP
    step_name: str
    for step_name in testcase_config.keys():
        _CURRENT_STEP = step_name.split(".")[-1]
        #repeat current step if "repeat" key > 0
        for i in range(0, testcase_config[step_name].get("repeat", 1)):
            inc_current_repeat(testcase_config[step_name], i + 1)
            nano_runner = NanoRunner(_ENV, step_name,
                                     testcase_config[step_name])
            nano_runner.run()


def handler(signal_received, frame):

    # Handle any cleanup here
    print('SIGINT or CTRL-C detected. Exiting gracefully')
    os._exit(0)


# class Pargs():
#     config_file = "speedsuite/testcases/nanolocal/run/6node_ws_change.json"


def main():
    global _SUITE_CONFIG
    signal(SIGINT, handler)
    args = parse_args()
    #args = Pargs

    _SUITE_CONFIG = ConfigReadWrite().read_json(args.config_file)
    testcase_config = load_testcase_config()
    total_runs, current_run = init_runs()

    validate_config()
    seuite_stats = StatsLogger()
    seuite_stats.new_testsuite(_ENV, _SUITE_CONFIG["testname"])

    while current_run < total_runs:
        try:
            init_testcase(current_run)
            run_steps(testcase_config)
        except:
            traceback.print_exc()
        finally:
            current_run = current_run + 1
            cleanup_testcase()  # join threads, close websockets

    seuite_stats.update_sql_end_date()


if __name__ == "__main__":
    main()
