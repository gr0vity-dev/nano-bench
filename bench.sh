# Authort : gr0vity
# Script :  2022-12-30
#           Check preconditions to run speedsuite.py
#           Run testcase defined in TEST_CONFIG
#           By default : Create a nano-local network of 1 node
#                        Enable voting on a ledger iwth 200k checked blocks
#                        Measure cps at 10%, 25% 50%, 75%, 90%, 99% and 100% cemented blocks    

docker_version=$1 #TODO: in config file, replace current docker_version with the one specified in the script
PYTHON_MIN_VERSION="(3,8,10)"
TEST_CONFIG="./speedsuite/testcases/nanolocal/bench/1node_bench.json"

#Exit early if wrong python version is installed
if ! python3 -c "import sys; assert sys.version_info >= $PYTHON_MIN_VERSION" > /dev/null; 
then 
    INSTALLED_PYTHON_VERSION=$(python3 -c "import sys; print(\"({0},{1},{2})\".format(sys.version_info.major,sys.version_info.minor,sys.version_info.micro))")
    echo ERROR : Bad python version $INSTALLED_PYTHON_VERSION
    echo Expected min. python version $PYTHON_MIN_VERSION
    exit 1
fi

#run virtual python environment if not already run
if ! [ -d "venv_nanolocal" ]; then
    ./setup_python_venv.sh
fi

# git init submodules if not already initiated
[ "$(ls -A ./submodules/nanolocal)" ] && git submodule update --init

#Run benchmark
./speedsuite.py $TEST_CONFIG

#Print results from all testruns
./venv_nanolocal/bin/python3 -c "from speedsuite.sql.query_testcase import NanoSqlQuery; print(NanoSqlQuery().query_cps_p25_to_p90())"