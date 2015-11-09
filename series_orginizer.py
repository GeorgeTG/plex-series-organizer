#!/usr/bin/env python3

import argparse
import re
from os import listdir, symlink, makedirs, remove
from os.path import isfile, join, splitext, isdir, abspath
from sys import argv,exit

class Colors(object):
    OKB= '\033[94m'
    OKG = '\033[92m'
    WRN = '\033[93m'
    ERR = '\033[91m'

    NRM = "\x1B[0m"
    RED = "\x1B[31m"
    GRN = "\x1B[32m"
    YEL = "\x1B[33m"
    BLU = "\x1B[34m"
    MAG = "\x1B[35m"
    CYN = "\x1B[36m"
    WHT = "\x1B[37m"
    BLD = '\033[1m'
    ULN = '\033[4m'
    RST = '\033[0m'

    @staticmethod
    def print_header(text):
        print(Colors.MAG + Colors.BLD + text + Colors.RST)

    @staticmethod
    def print_entry(entry):
        print(Colors.RED + ']> ' + Colors.GRN + entry + Colors.RST)

    @staticmethod
    def print_list(list_p ):
        for item in list_p:
            Colors.print_entry(item)

    def print_dict(dict_p, enum=False):
        for key, value in dict_p.items():
            Colors.print_entry('{0} <-> {1}'.format(key, value))

    @staticmethod
    def print_c(color, text):
        print(color + text + Colors.RST)

    @staticmethod
    def print_err(err):
        print("{0}{1}{2}{3}".format(Colors.ERR, '[ERROR] ', err, Colors.RST))

    @staticmethod
    def print_wrn(warn):
        print("{0}{1}{2}{3}".format(Colors.WRN, '[WARN] ', warn, Colors.RST))
class Bundle:
    def __init__(self, **entries):
        self.__dict__.update(entries)
    def as_dict(self):
        return self.__dict__

def dir_getfiles(directory):
    return [ f for f in listdir(directory) if isfile(join(directory,f)) ]

def check_file(path):
    if not isfile(path):
        Colors.print_err('Not a file: {0}'.format(path))
        return False
    return True

def check_dir(path):
    if not isdir(path):
        Colors.print_err('Not a directory: {0}'.format(path))
        return False
    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description='Fixes bad episode names by creating symlinks')

    parser.add_argument('--source','-i',
        type=str, metavar='[dir]',
        required=True, dest='source_dir',
        help="The source directory to scan for video files"
    )

    parser.add_argument('--match', '-m',
        type=str, metavar='[pattern]',
        dest='pattern', required=True,
        help = """
            The RegEx pattern to match episode number.
            Must extract said number as a group.
            """
    )

    parser.add_argument('--episodes', '-e',
        type=str, metavar='[file]',
        dest='episodes_file', default=None,
        help= """
            The file that contains all episodes.
            Should be in format number:name
            """
    )

    parser.add_argument('--season', '-s',
        type=int, metavar='[number]',
        required=True
    )

    parser.add_argument('--name', '-n',
        type=str, metavar='[name]',
        required=True,
        help = "Series name"
    )

    parser.add_argument('--dest', '-o',
        type=str, metavar='[dir]', dest='dest_dir',
        default=None, help="Destination directory"
    )

    parser.add_argument('--force','-f',
        action='store_true',
        help = "Force overwrite of links. WARNING: Data loss posible"
    )

    parser.add_argument('--create-dirs','-c',
        action='store_true', dest='create_dirs',
        help = "Create 'SeriesName/SeasonXX/ dirs in output dir"
    )

    parser.add_argument('--version',
        action='version', version='%(prog)s 0.5'
    )
    return parser.parse_args()


valid_ans = ['Y','y', 'N', 'n']
def prompt_yes_no(message):
    ans = None

    print('{0} [{1}]'.format(message, ', '.join(valid_ans)))
    while True:
        ans = str(input())
        if ans not in valid_ans:
            Colors.print_err("Valid answers: [{0}]".format(", ".join(valid_ans)))
        else:
            break

    if ans.lower() == 'n':
        return False
    else:
        return True

def scan_dir(directory, pattern):
    """
    Scans 'directory' for matching files according to regex 'pattern'.
        Returns: a dictionary with the follow format
        # "i" -> "whatever_whatever_[i]_name.mkv
    """
    regex = re.compile(pattern)
    matched_files={}

    #get all files from directory
    files = dir_getfiles(directory)

    Colors.print_header('Scanning for files...')
    for candinate in files:
        match = regex.match(candinate)
        if match:
            if len(match.groups()) != 1:
                print("File: {0} didn't match correctly".format(candinate))
                continue
            else:
                #we have a match and a group to obtain ep. number specified
                ep_num = match.group(1)

                Colors.print_entry('Matched episode [{0}] number: [{1}]'\
                        .format(candinate, ep_num))
                matched_files[ep_num] = candinate

    return matched_files

def parse_episodes_file(filename):
    """
    Parse given file to obtain episode names
    Current format is EpNumber:EpName for each line
        Returns: Dict:
            EpNum->EpName
    """
    episode_names = {}
    try:
        with open(filename, "r") as f:
            #all lines in file, striped from whitespace
            lines = [line.rstrip('\r\n') for line in f]

    except Exception as ex:
        print(str(ex))
        exit(-1)

    for i, line in enumerate(lines):
        parts = line.split(':')
        if len(parts) != 2:
            Colors.print_wrn('Line[{0}]: Bad format'.format(i+1))
            continue
        episode_names[parts[0]] = parts[1]

    return episode_names

def format_link(original_file, series_info, episode_info):
    #ShowName - sXXeYY - Optional_Info.ext
    args = series_info.as_dict().copy()
    args['ep_num'] = episode_info.number
    args['ep_name'] = episode_info.name
    _, ext = splitext(original_file)
    if args['ep_name']:
        fmt_str= '{name} - s{season:0>2}e{ep_num:0>2} - {ep_name}{0}'
    else:
        fmt_str= '{name} - s{season:0>2}e{ep_num:0>2}{0}'
    return fmt_str.format(ext, **args)

def prepare_links(files, series_info, episode_names=None):
    links_map = {}
    episode_info = Bundle()

    for ep_num, candinate in files.original.items():
        original_file = abspath(join(files.source_dir, candinate))
        if not files.dest_dir:
            files.dest_dir = files.source_dir

        if episode_names:
            if ep_num in episode_names:
                episode_info.name = episode_names[ep_num]
            else:
                episode_info.name = None
                Colors.print_wrn('Episode[{0}] not found in episodes file'.\
                        format(ep_num))

        episode_info.number = ep_num
        ep_filename = format_link(original_file, series_info, episode_info)

        links_map[original_file] = abspath(join(files.dest_dir, ep_filename))
    return links_map

def fix_with_file(files, series_info, options):
    if files.episodes_file and check_file(files.episodes_file):
        episode_names = parse_episodes_file(files.episodes_file)
        if len(episode_names) > 0:
            Colors.print_header('Found in episodes file:')
            Colors.print_dict(episode_names)
        else:
            episode_names = None
    else:
        episode_names = None

    if len(files.original) != len(episode_names):
        Colors.print_wrn(
                "Number of episodes mathced differs from definitions in file")
    if options.create_dirs:
        files.dest_dir = join(
                files.dest_dir,
                series_info.name,
                'Season {0:0>2}'.format(series_info.season)
        )

    links = prepare_links(files, series_info, episode_names)

    Colors.print_header('Theese links will be created:')
    Colors.print_list(list(links.values()))
    if not prompt_yes_no("Continue?"):
        print('Aborting...')
        exit(0)

    if not isdir(files.dest_dir):
        makedirs(abspath(files.dest_dir))

    #Force is specified, delete dest file
    if force and isfile(dest):
        print('[-f] Deleting existing file link {0}'.format(dest))
        remove(dest)

    try:
        print('Creating link {0}'.format(dest))
        symlink(original_file, dest)
    except Exception as ex:
        print(str(ex))


def main():
    args = parse_args()
    if not check_dir(args.source_dir):
        exit(-1)

    series_info = Bundle(**{
        'name': args.name,
        'season': args.season,
    })

    files_info = Bundle(**{
        'source_dir': args.source_dir,
        'dest_dir': args.dest_dir if args.dest_dir else args.source_dir,
        'episodes_file': args.episodes_file,
        'original': scan_dir(args.source_dir, args.pattern)
    })
    options = Bundle(**{
        'force': args.force,
        'create_dirs': args.create_dirs
    })
    fix_with_file(files_info, series_info, options)

if __name__=='__main__':
    main()
