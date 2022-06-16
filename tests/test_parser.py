import unittest
import _test_utils
from rawtypes.parser import Parser


class TestParser(unittest.TestCase):

    def test_parse(self):
        SRC = '''
void add(int a, inb b);

void default_bool(bool enable = true, bool disable = false);
'''
        parser = Parser.parse_source(SRC)

        f = parser.get_function('add')
        self.assertIsNotNone(f)

        f = parser.get_function('default_bool')
        self.assertIsNotNone(f)
        enable = f.params[0]
        disable = f.params[1]
        pass

    def test_struct_field(self):
        SRC = '''
struct S{ // STRUCT_DECL / RECORD_TYPE
    struct Value{ // FIELD_DECL / ELABORATED_TYPE
        int a;
    } value;
};
'''
        parser = Parser.parse_source(SRC)
        s = parser.get_struct('S')
        self.assertIsNotNone(s)

        f0 = s.fields[0]
        self.assertEquals('value', f0.name)

    def test_anonymous(self):
        SRC = '''
struct NVGcolor {
    union { // anonymous record
        float rgba[4];
        struct {
            float r, g, b, a;
        };
    };
};        
'''

        parser = Parser.parse_source(SRC)
        s = parser.get_struct('NVGcolor')
        self.assertIsNotNone(s)

        f0 = s.fields[0]
        self.assertTrue(f0.is_anonymous_type)

    def test_elaborate(self):
        SRC = '''
struct ImVec2
{
    float x, y;
};
struct ImVec4
{
    float x, y, z, w;
};
struct StyleVars
{
    float SlotRadius = 5.0f;
    ImVec2 ItemSpacing{8.0f, 4.0f};
    struct // anonymous elaborated
    {
        ImVec4 NodeBodyBg{0.12f, 0.12f, 0.12f, 1.0f};
        ImVec4 NodeBodyBgHovered{0.16f, 0.16f, 0.16f, 1.0f};
        ImVec4 NodeBodyBgActive{0.25f, 0.25f, 0.25f, 1.0f};
        ImVec4 NodeBorder{0.4f, 0.4f, 0.4f, 1.0f};
        ImVec4 NodeTitleBarBg{0.22f, 0.22f, 0.22f, 1.0f};
        ImVec4 NodeTitleBarBgHovered{0.32f, 0.32f, 0.32f, 1.0f};
        ImVec4 NodeTitleBarBgActive{0.5f, 0.5f, 0.5f, 1.0f};
    } Colors;
};        
'''

        parser = Parser.parse_source(SRC)
        s = parser.get_struct('StyleVars')
        self.assertIsNotNone(s)

        self.assertEquals(3, len(s.fields))
