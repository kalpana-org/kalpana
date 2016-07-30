
from os.path import join
import re

from PyQt4 import QtGui

from libsyntyche.common import local_path, read_file, read_json, write_file, kill_theming
from libsyntyche.entryviewlib import HTMLEntryView, EntryList

from common import Configable, keywordpatterns


class ChapterEntryList():

    def __init__(self):
        self.entries = {}

    def load_data(self, data):
        #completeflag = self.get_setting('complete flags')[0]
        completeflag = '[#done]'
        ch_rx = keywordpatterns['chapter'] + r'(?P<complete>\s*{}\s*)?'.format(re.escape(completeflag))
        sec_rx = keywordpatterns['section']
        desc_rx = keywordpatterns['description']
        tags_rx = keywordpatterns['tags']
        time_rx = keywordpatterns['time']
        chapters = re.split(r'\n(?=(?:>>\s+)?CHAPTER\s+\d+)', data)
        if len(chapters) == 1:
            print('no chapters found')
            return ''
        chapterlines = [c.count('\n')+1 for c in chapters]
        chapterlines[0] -= 1
        self.entries = {}
        for n, c in enumerate(chapters):
            if not c.strip():
                continue
            lines = c.splitlines()
            header = re.fullmatch(ch_rx, lines[0])
            cdata = {'num': header.group('num'),
                     'name': header.group('name'),
                     'complete': True if header.group('complete') else False,
                     'desc': None, 'time': None, 'tags': None,
                     'pos': sum(chapterlines[:n]),
                     'length': len(re.findall(r'\S+', c))}
            for l in lines[1:]:
                desc = re.fullmatch(desc_rx, l)
                tags = re.fullmatch(tags_rx, l)
                time = re.fullmatch(time_rx, l)
                if cdata['desc'] is None and desc:
                    cdata['desc'] = desc.group('desc')
                elif cdata['tags'] is None and tags:
                    cdata['tags'] = set(t.strip().lstrip('#')
                                        for t in tags.group(0).split(',')
                                        if t.strip())
                elif cdata['time'] is None and time:
                    cdata['time'] = time.group('time')
                else:
                    # if nothing matches then go to next chapter
                    break
            cdata['sections'] = self._get_sections(c, sec_rx, desc_rx)
            self.entries[n] = cdata

    def _get_sections(self, text, sec_rx, _):
        sections = []
        for n, line in enumerate(text.split('\n')):
            match = re.fullmatch(sec_rx, line)
            if match:
                section = {'payload': match.group('payload'),
                           'pos': n}
                sections.append(section)
        return sections

    def _get_sections_old(self, text, sec_rx, desc_rx):
        sectionchunks = re.split(r'\n(?=SECTION)', text)
        #print(sectionchunks)
        sectionlines = [s.count('\n')+1 for s in sectionchunks]
        sectionlines[0] -= 1
        sections = []
        for n, s in enumerate(sectionchunks[1:]):
            lines = s.splitlines()
            header = re.fullmatch(sec_rx, lines[0])
            section = {'name': None, 'desc': None,
                       'pos': sum(sectionlines[:n])}
            if header:
                section['name'] = header.group('name')
            desc = re.fullmatch(desc_rx, lines[1])
            if desc:
                section['desc'] = desc.group('desc')
            sections.append(section)
        return sections


    def write_data(self):
        pass

    def set_entry_value(self, entryid, attribute, newvalue):
        pass





def load_html_templates():
    path = lambda fname: local_path(join('templates', fname))
    return {
        'entry': read_file(path('entry_template.html')),
        'section': read_file(path('section_template.html')),
        'page': read_file(path('index_page_template.html')),
        'tags': read_file(path('tags_template.html'))
    }


class OverviewHTMLEntryView(HTMLEntryView):

    def format_entry(self, n, id_, entry):
        def format_title(num, name):
            out = 'Chapter {}'.format(num)
            if name:
                out += ' - ' + name
            return out
        def format_time(time):
            if not time:
                return ''
            else:
                return '&#128337; ' + time
        def format_tags(tags):
            if not tags:
                return ''
            return '&ndash; ' + '<wbr>'.join(
                self.templates['tags'].format(tag=t.replace(' ', '&nbsp;').replace('-', '&#8209;'),
                                    color='#888')#tagcolors.get(t, deftagcolor))
                for t in sorted(tags))
        def format_desc(desc):
            return desc if desc else '<span class="empty_desc">[no desc]</span>'
        def format_sections(sections):
            formattedsections = []
            for n, s in enumerate(sections):
                formattedsections.append(self.templates['section'].format(
                    id=n,
                    desc=s['payload']#s['desc'] if s['desc'] else '<span class="empty_desc">[no desc]</span>'
                ))
            return '\n'.join(formattedsections)
        fentry = {
            'id': id_,
            'title': format_title(entry['num'], entry['name']) + (' ✓' if entry['complete'] else ''),
            'length': entry['length'],
            'time': format_time(entry['time']),
            'tags': format_tags(entry['tags']),
            'desc': format_desc(entry['desc']),
            'sections': format_sections(entry['sections']),
            'complete': 'complete' if entry['complete'] else 'incomplete'
        }
        return self.templates['entry'].format(num=n, **fentry)


class Overview(QtGui.QWidget, Configable):
    def __init__(self, parent, settingsmanager):
        super().__init__(parent)
        self.init_settings_functions(settingsmanager)
        layout = QtGui.QVBoxLayout(self)
        kill_theming(layout)
        self.entrylist = ChapterEntryList()

        self.cssfname = join(self.get_path('config_dir'), '.index.css')
        self.generate_css(self.cssfname)
        self.view = OverviewHTMLEntryView(self, '#entry{}', '#hr{}',
                                          self.cssfname)
        self.view.templates = load_html_templates()
        layout.addWidget(self.view.webview, stretch=1)


    def generate_css(self, cssfname):
        def make_rgba(hexcol, alpha):
            if len(hexcol) == 3:
                rgb = [int(hexcol[i:i+1]*2, 16) for i in (0,1,2)]
            elif len(hexcol) == 6:
                rgb = [int(hexcol[i:i+2], 16) for i in (0,2,4)]
            return 'rgba({}, {}, {}, {})'.format(*rgb, alpha)

        css_template = read_file(local_path(join('templates', 'index_page.css')))
        style = read_json(self.get_path('style'))
        style['entry background'] = make_rgba(style['document text color'].lstrip('#'), 0.05)
        style['section background'] = style['entry background']
        disclaimer = '/* AUTOGENERATED! NO POINT IN EDITING THIS */\n\n'
        css = css_template.format(**style)
        write_file(cssfname, disclaimer + css)

    def wheelEvent(self, ev):
        self.view.wheelEvent(ev)


    def refresh_stuff(self):
        self.generate_css(self.cssfname)
        self.view.update_html(self.entrylist.entries)


    def set_data(self, text):
        self.entrylist.load_data(text)
        self.view.set_entries(self.entrylist.entries)
