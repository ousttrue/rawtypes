import unittest
import rawtypes.clang_util

SRC = '''
void add(int a, inb b);

void add(int a, int b)
{
    return a+b;
}
'''


class TestClangUtil(unittest.TestCase):

    def test_forward(self):
        tu = rawtypes.clang_util.get_tu(
            'tmp.h', unsaved=[rawtypes.clang_util.Unsaved('tmp.h', SRC)])

        def callback(*cursors):            
            print([c.spelling for c in cursors])
            return True

        rawtypes.clang_util.traverse(tu, callback)
