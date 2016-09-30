



class Section():

    def __init__(self, desc=None):
        self.line_count = 0
        self.desc = desc

    def __eq__(self, other):
        try:
            return self.line_count == other.line_count and\
                   self.desc == other.desc
        except:
            return False


class Chapter():

    def __init__(self, title='', complete=False):
        self.title = title
        self.complete = complete
        self.line_count = 0
        self.metadata_line_count = 0
        self.desc = None
        self.time = None
        self.tags = None
        self.sections = [Section()]

    def __eq__(self, other):
        try:
            return self.title == other.title and\
                   self.complete == other.complete and\
                   self.line_count == other.line_count and\
                   self.metadata_line_count == other.metadata_line_count and\
                   self.desc == other.desc and\
                   self.time == other.time and\
                   self.tags == other.tags and\
                   self.sections == other.sections
        except:
            return False


class ChapterIndex():

    def __init__(self):
        self.chapters = []
        self.chapter_keyword = 'CHAPTER'

    def parse_document(self, text):
        start_chars = self.chapter_keyword[0] + '[#🕑<'
        total_line_count = text.count('\n')
        lines = ((n, l) for n, l in enumerate(text.split('\n'))
                 if l and l[0] in start_chars)
        chapters = [Chapter()]
        current_chunk_start = 0
        consume_metadata = False
        last_n = 0
        for n, line in lines:
            if consume_metadata:
                if last_n == n:
                    if chapters[-1].desc is None and line.startswith('[[')\
                                            and line.rstrip().endswith(']]'):
                        chapters[-1].desc = line.rstrip()[2:-2].strip()
                        continue
                    elif chapters[-1].time is None and line[0] == '🕑':
                        chapters[-1].time = line[1:].strip()
                        continue
                    elif chapters[-1].tags is None and line[0] == '#':
                        chapters[-1].tags = {tag.strip()[1:]
                                             for tag in line.split(',') if tag.strip()}
                        continue
                chapters[-1].metadata_line_count = last_n - current_chunk_start
                current_chunk_start = last_n
                consume_metadata = False
            if line == 'CHAPTER' or line.startswith('CHAPTER ') or line.startswith('CHAPTER\t'):
                chapters[-1].sections[-1].line_count = n - current_chunk_start
                chapters.append(Chapter(
                    title=line[len('CHAPTER'):].strip('✓ \t'),
                    complete=line.rstrip().endswith('✓')
                ))
                current_chunk_start = last_n = n
                consume_metadata = True
            elif line.startswith('<<') and line.rstrip().endswith('>>'):
                chapters[-1].sections[-1].line_count = n - current_chunk_start
                chapters[-1].sections.append(Section(
                    desc=line.rstrip()[2:-2].strip()
                ))
                current_chunk_start = n
        chapters[-1].sections[-1].line_count = total_line_count - current_chunk_start + 1
        self.chapters = chapters
