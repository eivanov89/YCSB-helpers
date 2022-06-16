#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright 2022 YANDEX LLC. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License. See accompanying LICENSE file.

# See {@code README.md} for details.

# This script helps to simplify running `ycsb load` in parallel: depending on
# number of records to load and requested number of `ycsb load` instances it calculates
# `insertstart` and `insertcount` params and starts corresponding `ycsb load`
# processes. Also sometimes you don't have balancing node in your DB and want to split
# the load across multiple nodes.
#
# To split into multiple instances the original load command:
#
# > bin/ycsb load ydb -s -P workloads/workloada -p database=/Root/db1 \
# > -p endpoint=grpc://some1.net:2135 -p recordcount=1000
#
# you can run:
#
# > loader.py ydb -s -P workloads/workloada -p database=/Root/db1 \
# > -e "endpoint=grpc://some1.net:2135" -e "endpoint=grpc://some2.net:2135" -n 1000 -j 4
#
# this will run 4 instance of `ycsb load` in total: 2 instances per provided endpoint.
#
# I.e. to load 1B keys into YDB for workloads/workloada

import argparse
import logging
import math
import os
import pathlib
import subprocess
import sys
import time

logger = logging.getLogger("loader")
logging.basicConfig(level=logging.INFO)

# when there're more subprocs than CPU cores it is
# recommended to sleep between subinstances starts
SLEEP_BETWEEN_SUBPROCS_DEFAULT = 0.5

class Main(object):
    def __init__(self):
        super(Main, self).__init__()
        self.logger = logger
        self.subprocs = []

    def parse_args(self):
        self.parser = argparse.ArgumentParser(description="YCSB multi-instance loader")
        self.parser.add_argument("client", metavar="DB_CLIENT")
        self.parser.add_argument("-s", help="As in YCSB", dest="print_status", action="store_true")
        self.parser.add_argument("-p", help="As in YCSB", dest="p_args", action="append")
        self.parser.add_argument("-P", help="As in YCSB", dest="P_args", action="append")

        self.parser.add_argument(
            "-e", "--endpoint",
            dest="endpoints", action="append",
            help="Endpoints to split the load")

        self.parser.add_argument("-n", dest="record_count", help="Number of records to load", type=int)

        self.parser.add_argument("--total-records", dest="total_record_count",
            help="Number of total records in case of multiple loaders",
            type=int, default=0)

        self.parser.add_argument("--start-record", dest="start_record", help="Starting record in case of multiple loaders", type=int, default=0)
        self.parser.add_argument("-j", dest="split_factor", help="Number of instances to run", type=int)
        self.parser.add_argument("-o", "--logs-dir", dest="logs_dir", help="Create a log file for each YCSB instance")

        self.parser.add_argument(
            "--sleep", dest="sleep", type=float, default=SLEEP_BETWEEN_SUBPROCS_DEFAULT,
            help="Sleep time between starting subinstances")

        self.parser.add_argument(
            "--dry-run", dest="dry_run",
            action="store_true", help="Don't execute commands, just print")

        self.args = self.parser.parse_args()

    def execute_ycsb(self, base_args, batch_num, start_record, count):
        command = base_args.copy()
        command.append("-p")
        command.append("insertstart=" + str(int(start_record)))
        command.append("-p")
        command.append("insertcount=" + str(int(count)))

        endpoints_count = len(self.args.endpoints)
        if endpoints_count:
            command.append("-p")
            command.append(self.args.endpoints[batch_num % endpoints_count])

        self.logger.info(
            "Starting batch #%d from %d with size %d: %s",
            batch_num, start_record, count, " ".join(command))

        if self.args.dry_run:
            return

        if self.args.logs_dir:
            full_path = os.path.join(self.args.logs_dir, str(batch_num) + ".out")
            out = open(full_path, "w")

            full_path = os.path.join(self.args.logs_dir, str(batch_num) + ".err")
            err = open(full_path, "w")
        else:
            out = open(os.devnull, "w")
            err = open(os.devnull, "w")

        proc = subprocess.Popen(command, stdout=out, stderr=err)
        self.subprocs.append(proc)

    def run(self):
        self.parse_args()

        if self.args.split_factor <= 1:
            self.logger.error("-j argument must be greater than 1")
            return 1

        if self.args.record_count < self.args.split_factor:
            self.logger.error("-n must be greater than -j")
            return 1

        ycsb_path = "./bin/ycsb"

        if not pathlib.Path(ycsb_path):
            self.logger.error("No ycsb found at %s", ycsb_path)

        if self.args.logs_dir:
            if os.path.exists(self.args.logs_dir):
                self.logger.error("%s already exists", self.args.logs_dir)
                return 1
            try:
                pathlib.Path(self.args.logs_dir).mkdir(parents=True)
            except Exception as e:
                self.logger.error("Failed to create '%s': %s", self.args.logs_dir, str(e))
                return 1

        base_args = [ycsb_path, "load"]
        if self.args.print_status:
            base_args.append("-s")

        base_args.append(self.args.client)

        for arg in self.args.p_args:
            base_args.append("-p")
            base_args.append(arg)

        for arg in self.args.P_args:
            base_args.append("-P")
            base_args.append(arg)

        if self.args.total_record_count == 0:
           self.args.total_record_count  = self.args.record_count

        # note that it is total record count we want to upload
        base_args.append("-p")
        base_args.append("recordcount=" + str(self.args.total_record_count))

        start_time = time.time()

        batch_size = self.args.record_count / self.args.split_factor
        records_left = self.args.record_count
        for i in range(self.args.split_factor):
            start_record = self.args.start_record + i * batch_size
            count = batch_size
            if start_record + count > self.args.start_record + self.args.record_count:
                count = self.args.record_count - start_record
            self.execute_ycsb(base_args, i, start_record, count)
            if self.args.sleep:
                time.sleep(self.args.sleep)

        # now wait all finished
        for proc in self.subprocs:
            proc.wait()

        end_time = time.time()
        delta = math.ceil(end_time - start_time)
        if delta == 0:
            # avoids zero division in case of dry run
            delta += 1

        print("Finished in {} seconds ({} op/s)".format(delta, int(self.args.record_count / delta)))

if __name__ == "__main__":
    sys.exit(Main().run())
