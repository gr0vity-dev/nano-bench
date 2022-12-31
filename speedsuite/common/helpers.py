from time import strftime, gmtime, time
from math import ceil


class Formatting:

    def _percentile(self, data, percentile):
        n = len(data)
        p = n * percentile / 100
        if p.is_integer():
            return sorted(data)[int(p)]
        else:
            return sorted(data)[int(ceil(p)) - 1]

    def get_table(self, table, print_header=True):
        col_width = [max(len(str(x)) for x in col) for col in zip(*table)]

        for line in table:
            if print_header == False:
                print_header = True
                continue
            return ("| " + " | ".join("{:{}}".format(x, col_width[i])
                                      for i, x in enumerate(line)) + " |")

    def compute_stats(self, data, block_count_end, timeout_s):
        new_blocks = int(block_count_end.get("count", 0)) - int(
            data["block_count"].get("count", 0))
        new_cemented = int(block_count_end.get("cemented", 0)) - int(
            data["block_count"].get("cemented", 0))
        confirmations = [
            x["conf_duration"] for x in data["conf_lst"]
            if x["timeout"] == False
        ]
        timeouts = [x for x in data["conf_lst"] if x["timeout"]]
        conf_duration = time() - data["start_time"]

        gather_int = {
            "confs":
            len(confirmations),
            "timeouts":
            len(timeouts),
            "bps":
            new_blocks / conf_duration,
            "cps":
            new_cemented / conf_duration,
            "min_conf_s":
            min(confirmations) if len(confirmations) > 0 else -1,
            "max_conf_s":
            max(confirmations) if len(confirmations) > 0 else -1,
            "perc_50_s":
            self._percentile(confirmations, 50)
            if len(confirmations) > 0 else -1,
            "perc_75_s":
            self._percentile(confirmations, 75)
            if len(confirmations) > 0 else -1,
            "perc_90_s":
            self._percentile(confirmations, 90)
            if len(confirmations) > 0 else -1,
            "perc_99_s":
            self._percentile(confirmations, 99)
            if len(confirmations) > 0 else -1,
            "timeout_s":
            timeout_s,
            "total_s":
            conf_duration,
            "new_blocks":
            new_blocks,
            "new_cemented":
            new_cemented,
        }
        data["conf_lst"] = []
        data["block_count"] = block_count_end
        data["start_time"] = time()

        table_pr1 = (gather_int.keys(), [
            str(round(gather_int[x], 2)).ljust(8) for x in gather_int
        ])
        print(
            f'{strftime("%H:%M:%S", gmtime())} {self.get_table(table_pr1, print_header=True)}'
        )
        print(
            f'{strftime("%H:%M:%S", gmtime())} {self.get_table(table_pr1, print_header=False)}'
        )
