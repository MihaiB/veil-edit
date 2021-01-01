#! /usr/bin/env python3

import argparse
import getpass
import os
import shutil
import subprocess
import tempfile

ENV_VAR_NAME_EDITOR='EDITOR'
DEFAULT_EDITOR='vim'


def parse_args():
    p = argparse.ArgumentParser(description='''Edit an encrypted file
            (symmetric GPG).''',
            epilog='''Decrypt to 2 temporary files and open one in an editor.
            After the editor exits, if the files differ,
            ask the user to either discard the changes
            or overwrite the encrypted file.''')
    p.add_argument('--new', action='store_true', help='Create a new file.')
    p.add_argument('--editor',
            default=os.getenv(ENV_VAR_NAME_EDITOR, DEFAULT_EDITOR),
            help='''Invoked with one argument, the decrypted file.
            The default is taken from the environment variable ‘''' +
            ENV_VAR_NAME_EDITOR + '''’ if it exists, else it is ‘''' +
            DEFAULT_EDITOR + '''’. (your default is ‘%(default)s’)''')
    p.add_argument('--diff', default='meld',
            help='''Invoked with two arguments,
            the original file and the edited one,
            to show the difference between them. (default ‘%(default)s’)''')
    p.add_argument('file')
    return p.parse_args()


def readpass(confirm):
    p = getpass.getpass()
    if confirm:
        if getpass.getpass('Repeat password: ') != p:
            raise ValueError('Passwords do not match')
    return p


def encrypt(src, dest, passwd):
    args = [
        'gpg',
        #
        '--batch',
        '--no-symkey-cache',
        '--output', dest,
        '--passphrase-fd', '0', # docs say: --batch, --pinentry-mode loopback
        '--pinentry-mode', 'loopback',
        '--yes',
        #
        '--symmetric',
        src,
    ]

    subprocess.run(args, encoding='utf-8', input=passwd, check=True)


def decrypt(src, dest, passwd):
    args = [
        'gpg',
        #
        '--batch',
        '--no-symkey-cache',
        '--output', dest,
        '--passphrase-fd', '0', # docs say: --batch, --pinentry-mode loopback
        '--pinentry-mode', 'loopback',
        #
        '--decrypt',
        src,
    ]

    subprocess.run(args, encoding='utf-8', input=passwd, check=True)


def make_new_veil(dest, passwd):
    if os.path.lexists(dest):
        raise FileExistsError(dest)
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, 'empty')
        with open(src, 'x'):
            pass
        encrypt(src, dest, passwd)


def same_file_content(a, b):
    code = subprocess.run(['diff', '-q', a, b],
            stdout=subprocess.DEVNULL).returncode
    if code == 0:
        return True
    if code == 1:
        return False
    raise Exception('diff reported trouble: returncode {}'.format(code))


def confirm_overwrite(path):
    while True:
        answer = input('Overwrite {}? [y/n] '.format(path))
        if answer == 'y':
            return True
        if answer == 'n':
            return False
        print('Please answer ‘y’ or ‘n’')


def main():
    args = parse_args()
    passwd = readpass(confirm=args.new)
    if args.new:
        make_new_veil(args.file, passwd)

    edit_dir = tempfile.mkdtemp()
    edit_file = os.path.join(edit_dir, 'edit')
    decrypt(args.file, edit_file, passwd)

    try:
        with tempfile.TemporaryDirectory() as orig_dir:
            orig_file = os.path.join(orig_dir, 'orig')
            shutil.copyfile(edit_file, orig_file)

            subprocess.run([args.editor, edit_file], check=True)

            if same_file_content(orig_file, edit_file):
                print(args.file, 'not changed.')
            else:
                subprocess.run([args.diff, orig_file, edit_file], check=True)
                if confirm_overwrite(args.file):
                    encrypt(edit_file, args.file, passwd)
                    print(args.file, 'overwritten.')
                else:
                    print('Discarded changes to {}.'.format(args.file))
    except:
        print('Preserved the file being edited:', edit_file)
        raise

    shutil.rmtree(edit_dir)


if __name__ == '__main__':
    main()
