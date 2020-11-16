import main
import io
import os, os.path
import tempfile
import unittest, unittest.mock


class TestReadpass(unittest.TestCase):

    @unittest.mock.patch('getpass.getpass', spec_set=True, return_value='abc')
    def testNoConfirm(self, getpassP):
        self.assertEqual(main.readpass(False), 'abc')
        getpassP.assert_called_once_with()

    @unittest.mock.patch('getpass.getpass', spec_set=True,
            side_effect=['p1', 'p2'])
    def testConfirmDifferent(self, getpassP):
        with self.assertRaisesRegex(ValueError, '^Passwords do not match$'):
            main.readpass(True)

        call = unittest.mock.call
        calls = [call(), call('Repeat password: ')]
        getpassP.assert_has_calls(calls)
        self.assertEqual(getpassP.call_count, len(calls))

    @unittest.mock.patch('getpass.getpass', spec_set=True, return_value='xyz')
    def testConfirmSame(self, getpassP):
        self.assertEqual(main.readpass(True), 'xyz')

        call = unittest.mock.call
        calls = [call(), call('Repeat password: ')]
        getpassP.assert_has_calls(calls)
        self.assertEqual(getpassP.call_count, len(calls))


class TestEncryptDecrypt(unittest.TestCase):

    def testEncryptDecrypt(self):
        with tempfile.TemporaryDirectory() as d:
            orig, veiled, unveiled = (os.path.join(d, f) for f in
                    ('orig', 'veiled', 'unveiled'))
            message = 'Hello\nworld!'
            passwd = 'The veil of Ignorance'

            with open(orig, 'w', encoding='utf-8') as f:
                f.write(message)
            main.encrypt(orig, veiled, passwd)
            main.decrypt(veiled, unveiled, passwd)

            with open(unveiled, 'rb') as f:
                self.assertEqual(f.read(), message.encode('utf-8'))

            with open(veiled, 'rb') as f:
                self.assertNotEqual(f.read(), message.encode('utf-8'))

    def testEncryptOverwrites(self):
        with tempfile.TemporaryDirectory() as d:
            clear, veiled = (os.path.join(d, f) for f in ('clear', 'veiled'))
            passwd = 'public'
            with open(clear, 'x'):
                pass
            main.encrypt(clear, veiled, passwd)
            main.encrypt(clear, veiled, passwd)


class TestMakeNewVeil(unittest.TestCase):

    def testExistingFile(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, 'myfile')
            with open(f, 'x'):
                pass
            with self.assertRaisesRegex(FileExistsError, '^{}$'.format(f)):
                main.makeNewVeil(f, 'pass')

    def testNewFile(self):
        with tempfile.TemporaryDirectory() as d:
            veiled, unveiled = (os.path.join(d, f) for f in
                    ('veiled', 'unveiled'))
            passwd = 'pa-ss'
            main.makeNewVeil(veiled, passwd)
            main.decrypt(veiled, unveiled, passwd)
            self.assertEqual(os.lstat(unveiled).st_size, 0)


class TestSameFileContent(unittest.TestCase):

    def testSame(self):
        for content in (b'', b'\xff\x00\xee', 'hello'.encode('utf-8')):
            with tempfile.TemporaryDirectory() as d:
                a, b = (os.path.join(d, f) for f in ('a', 'b'))
                for path in (a, b):
                    with open(path, 'xb') as f:
                        f.write(content)

                self.assertIs(main.sameFileContent(a, b), True)

    def testDifferent(self):
        for aData, bData in (
                (b'', b'\0x00'),
                (b'\xa0', b'\xa1'),
                (text.encode('utf-8') for text in ('yes', 'no')),
                ):
            with tempfile.TemporaryDirectory() as d:
                a, b = (os.path.join(d, f) for f in ('a', 'b'))
                for path, content in ((a, aData), (b, bData)):
                    with open(path, 'xb') as f:
                        f.write(content)

                self.assertIs(main.sameFileContent(a, b), False)
                self.assertIs(main.sameFileContent(b, a), False)
