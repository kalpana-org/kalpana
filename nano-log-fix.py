#!/bin/python

# Script opens old log files, deletes older lines with same wordcount

import os, os.path

log_dir = '/home/cai/git-coding/nano_prev_stats'
logs = os.listdir(log_dir)
for log in logs:
    with open(log) as f: 
        f.readlines()
