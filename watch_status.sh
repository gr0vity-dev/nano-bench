DEFAULT_SLEEP=5
CURRENT_SLEEP="${1:-$DEFAULT_SLEEP}"
while true; do ./nl_run.py status && sleep $CURRENT_SLEEP ; done 
