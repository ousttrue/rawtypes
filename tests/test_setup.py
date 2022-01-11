import unittest

class TestSetup(unittest.TestCase):

    def test_setuptools(self):
        import setuptools
        import distutils.core
        self.assertNotEqual(setuptools.setup, distutils.core.setup)



if __name__ == '__main__':
    unittest.main()
