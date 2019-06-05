import os.path
import re
import yaml


def yaml_escape_unicode(text: str) -> str:
    r"""
    Return a string where all 32 bit characters are escaped.

    There's a bug in PyYAML that stops any character above \ufffe from being
    read. Fortunately other characters can still be read without problems as
    long as they're written in eight-character form: \U12345678.
    """
    def escape(match) -> str:
        return '\\U{:0>8}'.format(hex(ord(match.group()))[2:])
    return re.sub(r'[\ufffe-\U0001f9ff]', escape, text)


def load_config():
    with open(os.path.expanduser('~/.config/kalpana2/settings.yaml')) as f:
        raw_config = f.read()
        config = yaml.safe_load(yaml_escape_unicode(raw_config))
    return config


def index_chapters(fname: str, sep: str):
    chapters = [[]]
    chapter_start = False
    with open(fname) as f:
        for line in f:
            line = line.strip()
            if line.startswith(sep):
                chapters.append([])
                chapter_start = True
            elif chapter_start:
                if line.startswith('🕑') or line.startswith('[[') \
                        or line.startswith('#'):
                    continue
                else:
                    chapter_start = False
                    chapters[-1].append(line)
            else:
                chapters[-1].append(line)
    return chapters


def export_chapter(fname: str, chapter_num: int, fmt: str, sep: str) -> None:
    settings = load_config()
    chapters = index_chapters(fname, sep)
    print(len(chapters))
    if chapter_num < 0 or chapter_num >= len(chapters):
        print('invalid chapter')
        return
    lines = chapters[chapter_num]
    text = '\n'.join(t for t in lines if not t.startswith('<<')
                     and not t.startswith('%%'))
    export_formats = settings['export_formats']
    if fmt not in export_formats:
        print('Export format not recognized!')
        return
    for x in export_formats[fmt]:
        if 'selection_pattern' in x:
            text = replace_in_selection(text, x['pattern'], x['repl'],
                                        x['selection_pattern'])
        else:
            text = re.sub(x['pattern'], x['repl'], text)
    text = text.strip('\n\t ')
    with open('{}.chapter{}'.format(fname, chapter_num), 'w') as f:
        f.write(text + '\n')


def replace_in_selection(text: str, rx: str, rep: str, selrx: str) -> str:
    chunks = []
    selections = re.finditer(selrx, text)
    for sel in selections:
        x = re.sub(rx, rep, sel.group(0))
        chunks.append((sel.start(), sel.end(), x))
    # Do this backwards to avoid messing up the positions of the chunks
    for start, end, payload in chunks[::-1]:
        text = text[:start] + payload + text[end:]
    return text


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('fname')
    parser.add_argument('chapter', type=int)
    parser.add_argument('format', choices=('ao3', 'ff'))
    parser.add_argument('-s', '--chapter-sep', default='CHAPTER')
    args = parser.parse_args()
    export_chapter(args.fname, args.chapter, args.format, args.chapter_sep)
