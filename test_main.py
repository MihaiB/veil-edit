import main
import io
import os, os.path
import tempfile
import unittest, unittest.mock


class TestReadpass(unittest.TestCase):

    @unittest.mock.patch('getpass.getpass', spec_set=True, return_value='abc')
    def test_no_confirm(self, getpass_p):
        self.assertEqual(main.readpass(False), 'abc')
        getpass_p.assert_called_once_with()

    @unittest.mock.patch('getpass.getpass', spec_set=True,
            side_effect=['p1', 'p2'])
    def test_confirm_different(self, getpass_p):
        with self.assertRaisesRegex(ValueError, '^Passwords do not match$'):
            main.readpass(True)

        call = unittest.mock.call
        calls = [call(), call('Repeat password: ')]
        getpass_p.assert_has_calls(calls)
        self.assertEqual(getpass_p.call_count, len(calls))

    @unittest.mock.patch('getpass.getpass', spec_set=True, return_value='xyz')
    def test_confirm_same(self, getpass_p):
        self.assertEqual(main.readpass(True), 'xyz')

        call = unittest.mock.call
        calls = [call(), call('Repeat password: ')]
        getpass_p.assert_has_calls(calls)
        self.assertEqual(getpass_p.call_count, len(calls))


class TestEncryptDecrypt(unittest.TestCase):

    def test_encrypt_decrypt(self):
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

    def test_encrypt_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            clear, veiled = (os.path.join(d, f) for f in ('clear', 'veiled'))
            passwd = 'public'
            with open(clear, 'x'):
                pass
            main.encrypt(clear, veiled, passwd)
            main.encrypt(clear, veiled, passwd)


class TestMakeNewVeil(unittest.TestCase):

    def test_existing_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, 'myfile')
            with open(f, 'x'):
                pass
            with self.assertRaisesRegex(FileExistsError, '^{}$'.format(f)):
                main.make_new_veil(f, 'pass')

    def test_new_file(self):
        with tempfile.TemporaryDirectory() as d:
            veiled, unveiled = (os.path.join(d, f) for f in
                    ('veiled', 'unveiled'))
            passwd = 'pa-ss'
            main.make_new_veil(veiled, passwd)
            main.decrypt(veiled, unveiled, passwd)
            self.assertEqual(os.lstat(unveiled).st_size, 0)


class TestSameFileContent(unittest.TestCase):

    def test_same(self):
        for content in (b'', b'\xff\x00\xee', 'hello'.encode('utf-8')):
            with tempfile.TemporaryDirectory() as d:
                a, b = (os.path.join(d, f) for f in ('a', 'b'))
                for path in (a, b):
                    with open(path, 'xb') as f:
                        f.write(content)

                self.assertIs(main.same_file_content(a, b), True)

    def test_different(self):
        for a_data, b_data in (
                (b'', b'\0x00'),
                (b'\xa0', b'\xa1'),
                (text.encode('utf-8') for text in ('yes', 'no')),
                ):
            with tempfile.TemporaryDirectory() as d:
                a, b = (os.path.join(d, f) for f in ('a', 'b'))
                for path, content in ((a, a_data), (b, b_data)):
                    with open(path, 'xb') as f:
                        f.write(content)

                self.assertIs(main.same_file_content(a, b), False)
                self.assertIs(main.same_file_content(b, a), False)
