<!--
Copyright 2022 YANDEX LLC. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you
may not use this file except in compliance with the License. You
may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied. See the License for the specific language governing
permissions and limitations under the License. See accompanying
LICENSE file.
-->

## Quick start

This repository contains scripts to simplify YCSB usage. In examples we use [YDB](https://www.ydb.tech/) client, but
these scripts are applyable to any YCSB DB client.

Currently YDB client for YCSB is available in `ydb` branch of [YCSB-YDB](https://github.com/eivanov89/YCSB-YDB) repository.
Follow Readme instructions for YDB module to install it.

### loader.py

YCSB allows to load data in parallel as described in [Running multiple clients in parallel](https://github.com/brianfrankcooper/YCSB/wiki/Running-a-Workload-in-Parallel). To load in parallel user have to manually start multiple YCSB with different
options (main point is to start on different servers). But sometimes you want to start many instances on the same server.
`loader.py` simplifies this task: it automatically calculates required YCSB options and starts YCSB. It also allows to
specify different endpoints for each instance, which might be helpful when there is no balancing in either underlying DB client
or DB server node.

Script should be started inside YCSB, we recommend to use distribution (i.e. built package) VS source directory.

The following command

    $ python3 /PATH_TO_SCRIPTS/loader.py ydb \
    -s -P workloads/workloada -p database=/Root/db1 \
    -e endpoint=grpc://HOST1:2135 -e endpoint=grpc://HOST2:2135 -e endpoint=grpc://HOST3:2135 \
    -n 1000000 -j 100 -o ~/ycsb_logs_dir

will upload 1000000 records splitted between 100 YCSB instances. Each instance will write log to `~/ycsb_logs_dir`