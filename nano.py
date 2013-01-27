# Copyright cefyr 2011-2012

# This file is part of Kalpana.

# Kalpana is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Kalpana is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Kalpana. If not, see <http://www.gnu.org/licenses/>.


import datetime, os, os.path, re 

from math import ceil

try:
    from PySide import QtGui
    from PySide.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui
    from PyQt4.QtCore import Qt

class NaNoSidebar(QtGui.QPlainTextEdit):
    # Nano stuff including empty sidebar
    def __init__(self, parent):
        QtGui.QLineEdit.__init__(self, parent)
        self.parent = parent 
        self.setVisible(False)
        self.setReadOnly(True)
        self.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        font = QtGui.QFont()
        font.setFamily("Monospace")
        font.setPointSize(10)
        self.setFont(font)
        
        self.nano_width = 20 #TODO What is this?
        char_width = self.fontMetrics().averageCharWidth()
        self.setFixedWidth((self.nano_width + 1)*char_width)

        self.nano_day = 0 
        self.nano_mode = False
        # endpoint, goal, days and ideal_length are taken from config
        
        self.stats_dir = os.path.join(os.path.dirname(parent.cfgpath), 'nano')
        self.filename = #TODO
        self.logfile_days = #TODO
        self.logfile_chapters = #TODO

    def activate(self, arg):
        """
        Wrapper function to start NaNo mode.

        Called from terminal.
        """
        if arg.strip().isdigit():
            if int(arg.strip()) == 0:
                self.nano_mode = False
                return 'NaNo mode disabled', False
            elif int(arg.strip()) in range(1,self.days + 1):
                self.inano_day = int(arg.strip())
                self.nano_mode = True
                read_stats(self.nano_day, self.stats_dir)
                read_logs(self.logfile_days, self.nano_day)
                raw_text = self.parent.document.toPlainText() 
                sb_text = update_sb(raw_text, self.endpoint, self.goal, 
                                    self.words_today, self.days, self.nano_day, 
                                    self.ideal_length, self.stats)
                self.setPlainText(sb_text)
                return 'NaNo mode initiated', False
            else:
                return 'Invalid date', True
        else:
            return 'Invalid argument', True
        
    def update_wordcount(self):
        if self.nano_mode:
            wcount = sum(self.count_words(self.endpoint, 
                         self.parent.document.toPlainText())) 
        return wcount

    def save(self):
        if self.nanowidget.nano_mode:
            raw_text = self.parent.document.toPlainText() 
            sb_text = update_sb(raw_text, self.endpoint, self.goal, self.words_today, 
                      self.days, self.nano_day, self.ideal_length, self.stats)
            self.setPlainText(sb_text)
            write_logs()
            self.check_force_exit()
            #self.setPlainText(self.nanowidget.nanoGenerateStats())
            #self.nanoLogStats()

    def toggle_sidebar(self):
        """
        """
        if self.nano_mode:
            raw_text = self.parent.document.toPlainText() 
            sb_text = update_sb(raw_text, self.endpoint, self.goal, self.words_today, 
                      self.days, self.nano_day, self.ideal_length, self.stats)
            self.setPlainText(sb_text)
            self.setVisible(abs(self.isVisible()-1))

    def check_force_exit(self):
        """
        check_force_exit() replaces #16
        check force-exit requirements from #16
        """
        #TODO Write some code
        pass
    

def read_stats(nano_day, stats_dir):
    """
    Read logs from earlier years. 
    
    read_stats() replaces nanoExtractOldStats
    read old logs, extract stats from this day
        - file -> array
    """
    # if stats directory exists:
    stats = []
    if os.path.exists(stats_dir):
        raw_stats = os.listdir(self.stats_dir)
        for log in raw_stats:
            with open(log) as f:
                # daily_stats has lines of log for one year
                lines = f.readlines()
            stats_this_day = [log.split('.')] + 
                             [day.split(', ')[2] for day in lines 
                             if int(day.split(', ')[1]) == nano_day] 
            stats.append(stats_this_day)
        stats.sort()
    return stats 

def read_logs(logfile, nano_day):
    """
    Read log, return last day's wordcount.

    read_logs() replaces nanoCountWordsChapters + #12
    read current logs, #12
        - file -> array
    """
    with open(logfile) as f:
        log_lines = f.read().splitlines()
    logged_day = 0
    logged_words = 0
    for line in log_lines:
        logged_day = int(line.split(', ')[1])
        if logged_day < nano_day:
            logged_words = int(line.split(', ')[2])
        else:
            break
    return logged_words

def write_logs():
    """
    write_logs() replaces nanoLogStats
    write logs
        - array -> file
        - overwrite/non-overwrite, #21 
            The point is to keep the earliest of identical wordcounts.
    """
    #TODO Write some code
    pass

def count_words(raw_text, endpoint):
    """
    count_words() replaces nanoCountWordsChapters
    count words per chapter
    - exclude comments, #20
    - regex + file? -> array
    """
    # Join lines and remove comments.
    # Split into chapters at (newlines + chapter start)
    text = re.sub(r'\[.*?\]', '', raw_text, re.DOTALL)
    #TODO Maybe make chapter divisions less hard-coded?
    chapter_text = re.split(r'\n{3}(?=KAPITEL|CHAPTER)', text)
    # list comp, for each chapter:
    # remove words after endpoint
    # return length of given_chapter.split()
    # return total words as well?
    chapters = [len(re.findall(r'\S+', item)) 
                for item in chapter_text.split(endpoint)[0]]
    return chapters

def update_sb(raw_text, endpoint, goal, words_today, days, nano_day, ideal_length, stats):
    """
    update_sb() replaces nanoGenerateStats
    wordcounts -> sidebar

    Sidebar syntax:
        DAY nano_day
        % of total goal

        Chapter Words Remaining
        ...     ...   ...

        Total
        Remaining today
        Written today
        Earlier years:
        Year diff_from_this_year
    """
    #NOTE Handle width of sidebar
    form = '{}' #NOTE This should be that thing with right-justified shit
    chapters = count_words(raw_text, endpoint) 
    percent = total/goal
    diff_today = words_today - (goal - sum(chapters))/
                                    (days - nano_day)
    text = 'DAY {0}, {1:.2%}\n\n'.format(nano_day, percent)  
    for item in chapters:
        line = '{} {} {}\n'.format(chapters.index(item), item, 
                                   item - ideal_length)
        text += line
    text += '\nTOTAL {}\n'.format(sum(chapters))
    text += 'Today {}\n'.format() #NOTE What's the variable called?
    text += 'Todo {}\n'.format(diff_today)
    text += '\nEarlier stats\n'
    for item in stats:
        line = '{} {}\n'.format(item[0], item[1])
        text += line
    return text

