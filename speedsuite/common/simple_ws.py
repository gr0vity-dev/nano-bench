import json
import websocket
import threading
from .stats_logger import WebsocketConfirmationStats, WebsocketVoteStats
import time
import ssl


class RepeatedTimer(object):

    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
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
            self._timer = threading.Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


class SimpleWs:

    #def __init__(self, ws_url: str, rpc_url,node_name :str, rpc_user = None, rpc_password = None):
    def __init__(self,
                 ws_url: str,
                 node_name: str,
                 node_version: str,
                 ws_topics=["confirmation"],
                 current_step=""):
        self.ws_url = ws_url
        self.is_closed = False
        self.write_stats = False
        self.node_name = node_name
        self.ws_topics = ws_topics
        self.start_timer = time.time()
        if "confirmation" in ws_topics:
            self.stats_conf = WebsocketConfirmationStats(
                node_name, node_version, current_step)
        if "vote" in ws_topics: self.stats_vote = WebsocketVoteStats()
        #self.__init_variables()
        #self.bg = BlockGenerator(rpc_url, rpc_user=rpc_user, rpc_password=rpc_password)
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=lambda ws, msg: self.on_message(ws, msg),
            on_error=lambda ws, msg: self.on_error(ws, msg),
            on_close=lambda ws, msg, err: self.on_close(ws, msg, err),
            on_open=lambda ws: self.on_open(ws))
        # self.ws.run_forever()
        if ws_url.startswith("wss"):
            self.wst = threading.Thread(
                target=self.ws.run_forever,
                kwargs={"sslopt": {
                    "cert_reqs": ssl.CERT_NONE
                }},
                daemon=True)
        else:
            self.wst = threading.Thread(target=self.ws.run_forever,
                                        daemon=True)
        #self.wst.daemon = True
        self.wst.start()

    def is_final_vote(self, json_msg):
        if json_msg["time"] == "18446744073709551615": return True
        return False

    def write_ws_stats(self):
        self.write_stats = True

    def value_match(self, json, key, value):
        if key in json and json[key] == value:
            return True
        return False

    def topic_selector(self, message):
        json_msg = json.loads(message)

        if json_msg["topic"] == "confirmation":
            self.p_confirmation(json_msg)
        elif json_msg["topic"] == "vote":
            raise Exception("NOT IMPLEMENTED")
            #self.p_vote(json_msg)
        # elif json_msg["topic"] == "new_unconfirmed_block":
        #     self.p_new_unconfirmed_block(json_msg)
        # elif json_msg["topic"] == "stopped_election":
        #     self.p_stopped_election(json_msg)
        # elif json_msg["topic"] == "started_election":
        #     p_started_election(json_msg)
        else:
            pass
            #print("select else")

    def p_confirmation(self, json_msg):

        self.stats_conf.inc_confirmation_counter()
        block_hash = json_msg["message"]["hash"]
        self.stats_conf.receive_hash(block_hash)

    # def p_new_unconfirmed_block(self, json_msg):
    #     if json_msg["message"]["account"] in self.account_filter :
    #         self.req_counter["new_unconfirmed_block"] = self.req_counter["new_unconfirmed_block"] + 1
    #         block_hash = self.nano_rpc.block_hash(json_msg["message"])
    #         self.hash_list["new_unconfirmed_block"].append(block_hash)
    #     else :
    #         self.req_counter["new_unconf_blk_not_in_session"] = self.req_counter["new_unconf_blk_not_in_session"] + 1

    def on_message(self, ws, message):
        self.topic_selector(message)

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, msg, error):
        self.is_closed = True
        print(f"### websocket connection closed"
              )  # after { time.time() - self.start_timer} ###")

    def terminate(self):
        #print("websocket thread terminating...")
        self.ws.close()
        self.stats_conf.log_stats()
        #return self.data_collection

    def on_open(self, ws):
        #self.ws.send(json.dumps({"action": "subscribe", "topic": "new_unconfirmed_block"}))
        if "confirmation" in self.ws_topics:
            self.ws.send(
                json.dumps({
                    "action": "subscribe",
                    "topic": "confirmation",
                    "options": {
                        "include_election_info": "false",
                        "include_block": "true"
                    }
                }))

        # if "vote" in self.ws_topics:
        #     self.ws.send(
        #         json.dumps({
        #             "action": "subscribe",
        #             "topic": "vote",
        #             "options": {
        #                 "include_replays": "true",
        #                 "include_indeterminate": "true"
        #             }
        #         }))

        # ws.send(json.dumps({"action": "subscribe", "topic": "confirmation", "options": {"include_election_info": "true"}}))
        print("### websocket connection opened ###")
