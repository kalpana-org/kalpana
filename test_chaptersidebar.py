import unittest
from chaptersidebar import ChapterError, get_chapter_wordcounts,\
                           validate_chapter_strings, get_chapter_text,\
                           get_chapters_data

class GetChapterTextTest(unittest.TestCase):

    def setUp(self):
        self.lines = """\
fishies
>> CHAPTER 1
Lorem ipsum.
Line 2.

Oh hey!
>> CHAPTER 2


>> CHAPTER 3
>> CHAPTER 4""".splitlines()
        self.linenumbers = [0, 2, 7, 10, 11]

    def test_normal_chapter(self):
        result = get_chapter_text(1, self.lines, self.linenumbers)
        self.assertEqual(result, 'Lorem ipsum.\nLine 2.\n\nOh hey!')

    def test_prologue(self):
        result = get_chapter_text(0, self.lines, self.linenumbers)
        self.assertEqual(result, 'fishies')

    def test_empty_string_chapter(self):
        with self.assertRaisesRegex(ChapterError, r'(?i)\bonly\s+whitespace\b'):
            get_chapter_text(2, self.lines, self.linenumbers)

    def test_empty_chapter(self):
        with self.assertRaisesRegex(ChapterError, r'(?i)\bonly\s+whitespace\b'):
            get_chapter_text(3, self.lines, self.linenumbers)

    def test_chapter_on_last_line(self):
        with self.assertRaisesRegex(ChapterError, r'(?i)\bonly\s+whitespace\b'):
            get_chapter_text(4, self.lines, self.linenumbers)

    def test_nonexistant_chapter(self):
        with self.assertRaisesRegex(ChapterError, r'(?i)\binvalid\s+chapter\s+number\b'):
            get_chapter_text(5, self.lines, self.linenumbers)



class GetChapterDataTest(unittest.TestCase):

    def setUp(self):
        self.lines = """\
>> CHAPTER 1
Lorem ipsum.
Line 2.

>> CHAPTER 2
Exciting ending!
What will happen next!""".splitlines()
        self.prologuename = 'prologue'
        self.chapter_strings = [
            ['>> +CHAPTER (?P<num>\\d+) ?[:-] (?P<name>.+)', '{num} - {name}'],
            ['>> +CHAPTER (?P<num>\\d+)\\s*$', '{num}']
        ]

        self.linenumbers = [0, 1, 5]
        self.items = ['prologue\n   0', '1\n   4', '2\n   6']

    def test_default_run(self):
        result_linenumbers, result_items = \
            get_chapters_data(self.lines, self.prologuename, self.chapter_strings)
        self.assertEqual(self.linenumbers, result_linenumbers)
        self.assertEqual(self.items, result_items)

    def test_mixed_chapter_formats(self):
        lines = """\
>> CHAPTER 1
Lorem ipsum.
Line 2.

>> CHAPTER 2 - Fish
Exciting ending!
What will happen next!""".splitlines()
        result_linenumbers, result_items = \
            get_chapters_data(lines, self.prologuename, self.chapter_strings)
        self.assertEqual(self.linenumbers, result_linenumbers)
        items = ['prologue\n   0', '1\n   4', '2 - Fish\n   6']
        self.assertEqual(items, result_items)

    def test_chapter_on_last_line(self):
        lines = """\
>> CHAPTER 1
Lorem ipsum.
Line 2.

>> CHAPTER 2""".splitlines()
        result_linenumbers, result_items = \
            get_chapters_data(lines, self.prologuename, self.chapter_strings)
        self.assertEqual(self.linenumbers, result_linenumbers)
        items = ['prologue\n   0', '1\n   4', '2\n   0']
        self.assertEqual(items, result_items)

    def test_no_lines(self):
        with self.assertRaises(ChapterError):
            get_chapters_data([], self.prologuename, self.chapter_strings)

    def test_no_matching_lines(self):
        lines = """\
>> Episode 1
Lorem ipsum.
Line 2.

>> Episode 2
Exciting ending!
What will happen next!""".splitlines()
        with self.assertRaises(ChapterError):
            get_chapters_data(lines, self.prologuename, self.chapter_strings)

    def test_invalid_chapter_regex(self):
        chapter_strings = [
            ['>> +CHAPTER (?P<num>\\d+)( ?[:-] (?P<name>.+))?', '{num} - {name}'],
        ]
        with self.assertRaisesRegex(ChapterError, 'broken settings'):
            get_chapters_data(self.lines, self.prologuename, chapter_strings)


class GetChapterWordcountsTest(unittest.TestCase):

    def test_default_run(self):
        lines = """\
>> CHAPTER 1
Lorem ipsum.
Line 2.

>> CHAPTER 2
Exciting ending!
What will happen next!""".splitlines()
        chapter_line_numbers = [0, 1, 5]
        wordcounts = get_chapter_wordcounts(chapter_line_numbers, lines)
        self.assertEqual(wordcounts, [0, 4, 6])

    def test_default_run_with_prologue(self):
        lines = """\
A prologue! Yes! How exciting.
And some more...
>> CHAPTER 1
Lorem ipsum.
Line 2.

>> CHAPTER 2
Exciting ending!
What will happen next!""".splitlines()
        chapter_line_numbers = [0, 3, 7]
        wordcounts = get_chapter_wordcounts(chapter_line_numbers, lines)
        self.assertEqual(wordcounts, [8, 4, 6])

    def test_no_lines_at_all(self):
        lines = []
        chapter_line_numbers = []
        wordcounts = get_chapter_wordcounts(chapter_line_numbers, lines)
        self.assertEqual(wordcounts, [])

    def test_no_chapters(self):
        lines = """\
Lorem ipsum dolor sit amet, consectetur adipisicing elit.
Sed do eiusmod tempor.

Incididunt ut labore et dolore magna aliqua.""".splitlines()
        chapter_line_numbers = [0]
        wordcounts = get_chapter_wordcounts(chapter_line_numbers, lines)
        self.assertEqual(wordcounts, [19])

    def test_empty_chapters(self):
        lines = """\

>> CHAPTER 1
>> CHAPTER 2


>> CHAPTER 3


""".splitlines()
        chapter_line_numbers = [0, 2, 3, 6]
        wordcounts = get_chapter_wordcounts(chapter_line_numbers, lines)
        self.assertEqual(wordcounts, [0, 0, 0, 0])



class ValidateChapterStringsTest(unittest.TestCase):

    def test_valid_data(self):
        chapter_strings = [
            ['>> +CHAPTER (?P<num>\\d+) ?[:-] (?P<name>.+)', '{num} - {name}'],
            ['>> +CHAPTER (?P<num>\\d+)\\s*$', '{num}']
        ]
        self.assertIsNone(validate_chapter_strings(chapter_strings))

    def test_invalid_regex(self):
        chapter_strings = [
            ['>> +CHAPTER (?P<num>\\d+)) ?[:-] (?P<name>.+)', '{num} - {name}'],
            ['>> +CHAPTER (?P<num>\\d+)\\s*$', '{num}']
        ]
        with self.assertRaises(AssertionError):
            validate_chapter_strings(chapter_strings)

    def test_empty_string_data(self):
        chapter_strings = [
            ['   ', '{num} - {name}'],
            ['>> +CHAPTER (?P<num>\\d+)\\s*$', '']
        ]
        with self.assertRaises(AssertionError):
            validate_chapter_strings(chapter_strings)

    def test_nonstring_data(self):
        chapter_strings = [
            [12, 1555]
        ]
        with self.assertRaises(AssertionError):
            validate_chapter_strings(chapter_strings)

    def test_empty_lists(self):
        chapter_strings = [
            [],
            ['>> +CHAPTER (?P<num>\\d+)\\s*$', '{num}']
        ]
        with self.assertRaises(AssertionError):
            validate_chapter_strings(chapter_strings)

    def test_wrong_size_lists(self):
        chapter_strings = [
            ['>> +CHAPTER (?P<num>\\d+)\\s*$', '{num}', 'another one?'],
            ['>> +CHAPTER (?P<num>\\d+)\\s*$', '{num}']
        ]
        with self.assertRaises(AssertionError):
            validate_chapter_strings(chapter_strings)

    def test_not_matching_regex_and_template(self):
        chapter_strings = [
            ['>> +CHAPTER (?P<foo>\\d+) ?[:-] (?P<bar>.+)', '{num} - {name}'],
            ['>> +CHAPTER (?P<num>\\d+)\\s*$', '{fishies}']
        ]
        with self.assertRaises(AssertionError):
            validate_chapter_strings(chapter_strings)