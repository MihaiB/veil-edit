#! /usr/bin/env python3

import argparse
import getpass
import os
import shutil
import subprocess
import tempfile

ENV_VAR_NAME_EDITOR='EDITOR'
DEFAULT_EDITOR='vim'


def parseArgs():
    p = argparse.ArgumentParser(description='''Edit an encrypted file
            (symmetric GPG).''',
            epilog='''Decrypt to 2 temporary files and open one in an editor.
            After the editor exits, if the files differ,
            ask the user to discard the changes
            or overwrite the encrypted file.''')
    p.add_argument('--new', action='store_true', help='Create a new file.')
    p.add_argument('--editor',
            default=os.getenv(ENV_VAR_NAME_EDITOR, DEFAULT_EDITOR),
            help='''Invoked with one argument, the decrypted file.
            The default is taken from the environment variable ''' +
            ENV_VAR_NAME_EDITOR + ''' if it exists, else it is ''' +
            DEFAULT_EDITOR + '''. (your default is %(default)s)''')
    p.add_argument('--diff', default='meld',
            help='''Invoked with two arguments,
            the original file and the edited one,
            to show the difference between them. (default %(default)s)''')
    p.add_argument('file')
    return p.parse_args()


def readpass(confirm):
    p = getpass.getpass()
    if confirm:
        if getpass.getpass('Repeat password: ') != p:
            raise ValueError('Passwords do not match')
    return p


def encrypt(src, dest, passwd):
    subprocess.run(['gpg', '--symmetric', '--batch', '--yes',
        '--passphrase-fd', '0', '--output', dest, src],
        encoding='utf-8', input=passwd, check=True)


def decrypt(src, dest, passwd):
    subprocess.run(['gpg', '--decrypt', '--batch',
        '--passphrase-fd', '0', '--output', dest, src],
        encoding='utf-8', input=passwd, check=True)


def makeNewVeil(dest, passwd):
    if os.path.lexists(dest):
        raise FileExistsError(dest)
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, 'empty')
        with open(src, 'x'):
            pass
        encrypt(src, dest, passwd)


def sameFileContent(a, b):
    code = subprocess.run(['diff', '-q', a, b],
            stdout=subprocess.DEVNULL).returncode
    if code == 0:
        return True
    elif code == 1:
        return False
    else:
        raise Exception('diff reported trouble: returncode {}'.format(code))


def confirmOverwrite(path):
    while True:
        answer = input('Overwrite {}? [y/n] '.format(path))
        if answer == 'y':
            return True
        if answer == 'n':
            return False
        print('Please answer ‘y’ or ‘n’')


def main():
    args = parseArgs()
    passwd = readpass(confirm=args.new)
    if args.new:
        makeNewVeil(args.file, passwd)

    editDir = tempfile.mkdtemp()
    editFile = os.path.join(editDir, 'edit')
    decrypt(args.file, editFile, passwd)

    try:
        with tempfile.TemporaryDirectory() as origDir:
            origFile = os.path.join(origDir, 'orig')
            shutil.copyfile(editFile, origFile)

            subprocess.run([args.editor, editFile], check=True)

            if sameFileContent(origFile, editFile):
                print(args.file, 'not changed.')
            else:
                subprocess.run([args.diff, origFile, editFile], check=True)
                if confirmOverwrite(args.file):
                    encrypt(editFile, args.file, passwd)
                    print(args.file, 'overwritten.')
                else:
                    print('Discarded changes to {}.'.format(args.file))
    except:
        print('Preserved the file being edited:', editFile)
        raise
    else:
        shutil.rmtree(editDir)


if __name__ == '__main__':
    main()
