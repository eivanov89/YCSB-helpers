#!/bin/bash
# This script is YDB specific in sence of YCSB client-related arguments.
#
# Note that you must have ENDPOINT in env or add it here, same about
# YDB_ACCESS_TOKEN_CREDENTIALS variable.

DB="/Root/db1"
SLEEP_BETWEEN="10m"

# data load settings
RECORDS_COUNT=100000000
LOAD_INSTANCES=128

# data run settings
THREADS=256
OPERATIONS_COUNT=operationcount

echodate()
{
    echo `date +%y/%m/%d_%H:%M:%S`:: $*
}

drop()
{
    # just to remove DB if exists (dropOnClean)
    ./bin/ycsb load ydb -P workloads/workloada -p database=$DB \
        -p maxparts=1 -p endpoint=$ENDPOINT \
        -p dropOnInit=true -p dropOnClean=true -p recordcount=100
}

set -x

echodate "Started"

drop

echodate "Cleanup done, loading data for workloads/workloada"

python3 ~/loader.py ydb -P workloads/workloada -p database=$DB -p maxparts=256 \
    -p maxpartsize=1000000 -e endpoint=$ENDPOINT -n $RECORDS_COUNT -j $LOAD_INSTANCES  -p insertInflight=10

sleep $SLEEP_BETWEEN
echodate "Starting workloada"

./bin/ycsb run ydb -s -p database=$DB -p endpoint=$ENDPOINT -p maxparts=256 -p maxpartsize=1000000 \
    -P workloads/workloada \
    -p recordcount=$RECORDS_COUNT -p operationcount=$OPERATIONS_COUNT -threads $THREADS


sleep $SLEEP_BETWEEN
echodate "Starting workloadb"

./bin/ycsb run ydb -s -p database=$DB -p endpoint=$ENDPOINT -p maxparts=256 -p maxpartsize=1000000 \
    -P workloads/workloadb \
    -p recordcount=$RECORDS_COUNT -p operationcount=$OPERATIONS_COUNT -threads $THREADS

sleep $SLEEP_BETWEEN
echodate "Starting workloadc"

./bin/ycsb run ydb -s -p database=$DB -p endpoint=$ENDPOINT -p maxparts=256 -p maxpartsize=1000000 \
    -P workloads/workloadc \
    -p recordcount=$RECORDS_COUNT -p operationcount=$OPERATIONS_COUNT -threads $THREADS

sleep $SLEEP_BETWEEN
echodate "Starting workloadf"

./bin/ycsb run ydb -s -p database=$DB -p endpoint=$ENDPOINT -p maxparts=256 -p maxpartsize=1000000 \
    -P workloads/workloadf \
    -p recordcount=$RECORDS_COUNT -p operationcount=$OPERATIONS_COUNT -threads $THREADS

sleep $SLEEP_BETWEEN
echodate "Starting workloadd"

./bin/ycsb run ydb -s -p database=$DB -p endpoint=$ENDPOINT -p maxparts=256 -p maxpartsize=1000000 \
    -P workloads/workloadd \
    -p recordcount=$RECORDS_COUNT -p operationcount=$OPERATIONS_COUNT -threads $THREADS

drop

sleep $SLEEP_BETWEEN
echodate "Cleanup done, loading data for workloads/workloade"


python3 ~/loader.py ydb -P workloads/workloade -p database=$DB -p maxparts=256 \
    -p maxpartsize=1000000 -e endpoint=$ENDPOINT -n $RECORDS_COUNT -j 128 -p insertInflight=10

sleep $SLEEP_BETWEEN
echodate "Starting workloade"

./bin/ycsb run ydb -s -p database=$DB -p endpoint=$ENDPOINT -p maxparts=256 -p maxpartsize=1000000 \
    -P workloads/workloade \
    -p recordcount=$RECORDS_COUNT -p operationcount=$OPERATIONS_COUNT -threads $THREADS

echodate "All done"