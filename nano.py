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
        #self.nanoWidth = 20
        # size is important
        charWidth = self.fontMetrics().averageCharWidth()
        self.setFixedWidth((self.nanoWidth + 1)*charWidth)

        self.nano_day = 0 
        self.nanoMode = False
        # endpoint, goal, days and idealChLength are taken from config
        self.stats_dir = os.path.join(os.path.dirname(parent.cfgpath), 'nano')

    def activate(self, arg):
        """
        At nn [cmd_arg], check cmd_arg for errors
        read_stats()
        read_logs()
        update_sb()
        """
        #TODO Double-check this code, change variables and shit
        if arg.strip().isdigit():
            if int(arg.strip()) == 0:
                self.nanoMode = False
                return 'NaNo mode disabled', False
            elif int(arg.strip()) in range(1,self.days + 1):
                self.myDay = int(arg.strip())
                self.nanoMode = True
                read_stats(self.nano_day, self.stats_dir)
                self.read_logs()
                self.update_sb()
                self.setPlainText(update_sb())
                return 'NaNo mode initiated', False
            else:
                return 'Invalid date', True
        else:
            return 'Invalid argument', True

    def read_logs(self):
        """
        read_logs() replaces nanoCountWordsChapters + #12
        read current logs, #12
            - file -> array
        """
        #TODO Write some code
        pass
        
    def update_wordcount(self):
        if self.nanoMode:
            wcount = sum(self.count_words(self.endPoint, 
                         self.parent.document.toPlainText())) 
        return wcount

    def nanoCountWordsChapters(self):
        """
        Count words per chapter, create current wordcount as chapter array and
        total wordcount. 
        Split chapter at text 'KAPITEL' or 'CHAPTER'.
        Should override updateWordCount.
        """
        # Join lines and remove comments.
        # Split into chapters at (newlines + chapter start)
        text = re.sub(r'\[.*?\]', '', self.parent.document.toPlainText(), re.DOTALL)
        chapterText = re.split(r'\n{3}(?=KAPITEL|CHAPTER)', text)
        self.wordsPerChapter = []
        self.accWcount = 0
        for n,i in enumerate(chapterText):
            chLength = len(re.findall(r'\S+', i.split(self.endPoint)[0]))
            self.wordsPerChapter.append(chLength)
            self.accWcount += chLength
        # Very much stolen from updateWordCount()
        if not self.accWcount == self.parent.wt_wordcount:
            self.parent.wt_wordcount = self.accWcount
            self.parent.updateWindowTitle()

    def save(self):
        if self.nanowidget.nanoMode:
            raw_text = self.parent.document.toPlainText() 
            update_sb(raw_text, self.endPoint, self.goal, self.words_today, 
                      self.days, self.nano_day, self.ideal_length, self.stats):
            write_logs()
            self.check_force_exit()
            #self.setPlainText(self.nanowidget.nanoGenerateStats())
            #self.nanoLogStats()

    def write_logs(self):
        """
        write_logs() replaces nanoLogStats
        write logs
            - array -> file
            - overwrite/non-overwrite, #21 
                The point is to keep the earliest of identical wordcounts.
        """

    def nanoLogStats(self):
        """
        Check if there is a statistics file; if not, create one.
        Look for filename.log 
        This function is run during saving.

        Logfile part 1, written in stat1:
        STATISTICS FILE
        filename
        Date, time, myDay, total wordcount
        
        Logfile part 2, written in stat2:
        CHAPTER = WORDS
        Chapter number = wordcount
        
        BONUS HAMSTER:
        Read yesterday's last wordcount!
        """
        logfilename = self.parent.filename + '.log'
        thistime = datetime.datetime.today()
        logstring = '{0}, {1} = {2}\n'
        stat1 = logstring.format(thistime.strftime('%Y-%m-%d %H:%M:%S'), 
                                 self.myDay, self.accWcount)
        stat2 = []
        for n,ch in enumerate(self.wordsPerChapter):
            stat2.append('{0} = {1}\n'.format(n, ch))
        if not os.path.isfile(logfilename):
            with open(logfilename, 'w', encoding='utf-8') as f:
                logHeader = 'STATISTICS FILE\n{0}\n\nDAY, MY DAY = WORDS\nCHAPTER = WORDS\n\n'.format(self.parent.filename) 
                f.write(logHeader)
        with open(logfilename, 'r', encoding='utf-8') as lr:
            logLines = lr.readlines()
            h = logLines.index('DAY, MY DAY = WORDS\n')
            i = logLines.index('CHAPTER = WORDS\n')
            lines = sorted(logLines[h+1:i])
            for line in lines:
                dayWcount = line.split(',')[1].strip()
                if int(dayWcount.split(' = ')[0]) < self.myDay:
                    self.myLastWcount = int(dayWcount.split(' = ')[1])
        with open(logfilename, 'w', encoding='utf-8') as l:
            newLines = logLines[:i] + [stat1] + [logLines[i]] + stat2
            l.writelines(newLines)

    def nanoExtractOldStats(self):
        """
        Read *_stats.txt files from prevStatsDir. Put them in array where row
        number corresponds to day, with year being in first row.
        Should be run at startup or when NaNo modes is turned on.
        """
        prevStatsDir = 'nano_prev_stats'
        self.oldStats = []
        statsFiles = []
        prevStatsDirPath = os.path.join(os.path.dirname(self.parent.filename), 
                                        prevStatsDir) 
        try:
            # List of filenames without paths
            statsFiles = os.listdir(os.path.join(os.path.dirname(self.parent.filename), 
                                    prevStatsDir))
        except OSError:
            pass
        else:
            for stFile in statsFiles:
                with open(os.path.join(prevStatsDirPath, stFile), 'r', 
                                 encoding='utf-8') as f:
                    statsByYearUnsplit = f.readlines()
                statsByYear = []
                for line in statsByYearUnsplit:
                    if len(line.split('\t'))>1:
                        line = line.split('\t')[1] 
                    statsByYear.append(line)
                self.oldStats.append(statsByYear)
        self.oldStats.sort()

    def toggle_sidebar(self):
        """
        """
        if self.nanoMode:
            self.update_sb()
            self.setVisible(abs(self.isVisible()-1))

    def nanoToggleSidebar(self):
        """
        Generate stats and show/hide NaNo sidebar.
        Ctrl P does this.
        """
        if self.nanoMode:
            self.setPlainText(self.nanoGenerateStats())
            self.setVisible(abs(self.isVisible()-1))

    def toggle(self):
        update_sb()


    def nanoGenerateStats(self):
        """
        Pick config data and wordcounts and return the text for the statistics
        window as a string.
        """
        # Total width of stats window is hard-coded :(
        w = self.nanoWidth - 13
        # Building the array
        statsText = ['DAY {0}, {1:.2%}\n\n'.format(self.myDay, 
                     float(self.accWcount)/float(self.goal))]
        formStr = '{0:<{1}}{2:>5}{3:>7} \n'
        self.goalToday = int(ceil(float(self.goal)/float(self.days))*self.myDay)
        self.goalYesterday = int(ceil(float(self.goal)/float(self.days))
                                                        *(self.myDay - 1))
        writtenToday = self.accWcount - self.myLastWcount
        diffToDaygoal = writtenToday - (self.goalToday - self.goalYesterday)
        for n,ch in enumerate(self.wordsPerChapter):
            if not n:
                statsText.append(formStr.format(n, w, ch, ''))
            else:
                statsText.append(formStr.format(n, w, ch, ch - self.idealChLen))
        statsText.append(formStr.format('TOTAL', w, self.accWcount,
                         self.accWcount - self.goal))
        statsText.append('\n')
        statsText.append(formStr.format('GOAL', w, 
                         self.goalToday, self.accWcount - self.goalToday))
        statsText.append(formStr.format('TODAY', w, writtenToday, 
                                        diffToDaygoal))
        statsText.append('\nPREVIOUSLY\n')
        prevStr = '{0:<{1}}{2:>5}{3:>7} \n' 
        for year in self.oldStats:
            # year is [20XX, words, words, words]
            diff = self.accWcount - int(year[self.myDay].strip())
            try:
                statsText.append(prevStr.format(year[0].strip(), w, 
                                                year[self.myDay].strip(), diff))
            except IndexError:
                pass

        return ''.join(statsText)

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

