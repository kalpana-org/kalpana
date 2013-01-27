#!/bin/python

# Script opens old log files, splits them into day log and chapter log, then
# deletes older lines with same wordcount

import os, os.path

head_days = 'STATISTICS FILE - DAYS'
head_chapters = 'STATISTICS FILE - CHAPTERS'
# filename\n\n
dayline = 'DAY, MY DAY = WORDS'
randomday = '2011-11-01 13:44:03, 1 = 789'
chapterline = 'CHAPTER = WORDS'
randomchapter = '10 = 3571'

log_dir = '/home/cai/gitcode/splitlogs'
logs = os.listdir(log_dir)
for log in logs:
    print('*** START *** \nLog file:', log)
    day_log = log + 'd'
    chapter_log = log + 'c'
    with open(log) as f: 
        raw_lines = f.read().splitlines()
    print('Log reading successful')
    for line in raw_lines:
        if line == chapterline:
            splitpoint = raw_lines.index(line)
            print('Found chapterline:', splitpoint)
            head_d = '{}\n{}\n\n{}\n'.format(head_days, raw_lines[1], dayline)
            head_c = '{}\n{}\n\n'.format(head_chapters, raw_lines[1])
            logd = head_d + '\n'.join(raw_lines[4:splitpoint]) + '\n'
            logc = head_c + '\n'.join(raw_lines[splitpoint:]) + '\n'
            with open(day_log, 'w') as d:
                print('Writing to day log...')
                d.write(logd)
            print('Closed day log')
            with open(chapter_log, 'w') as c:
                print('Writing to chapter log...')
                c.write(logc)
            print('Closed chapter log')
    print('FINISHED with log.')
print('Split finished')

day_files = [log for log in os.listdir(log_dir) if log[-1] == 'd']
print(day_files)
for item in day_files:
    print('Opening...', item)
    with open(item) as f:
        raw_text = f.read().splitlines()
    print('Read success.')
#    unique_lines = [line for line in raw_text[4:] if not int(line.split(' = ')[-1]) == ]
    last_unique = 0
    this_day = 0
    doubles = 0
    new_line = []
    for line in raw_text[4:]:
        day = int(line.split(', ')[-1].split(' = ')[0])
        words = int(line.split(' = ')[-1])
        if not words == last_unique:
            new_line.append(line)
            last_unique = words
            this_day = day
        elif not this_day == day:
            new_line.append(line)
            last_unique = words
            this_day = day
    print('Finished checking.')
    new_item = item + '.new'
    with open(new_item, 'w') as nf:
        nf.write('\n'.join(new_line) + '\n')
    print('New file written')
print('It is finished!!')
