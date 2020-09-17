from argparse import ArgumentParser, ArgumentTypeError
import importlib
from os.path import isdir


def dir_path(path):
    if isdir(path):
        return path
    else:
        raise ArgumentTypeError("'%s' is not a valid path" % path)


def execute():
    parser = ArgumentParser(
        prog='ldbc_snb_grblas',
        description="Calculate LDBC SNB BI queries using GraphBLAS."
    )

    parser.add_argument("queryid", type=int, help="Number of desired query to run.")
    parser.add_argument("datadir", type=dir_path, help="Folder containing input date.")
    parser.add_argument("params", nargs='*', help="Other query specific parameters.")
    args = parser.parse_args()

    try:
        query = importlib.import_module('.queries.q%d' % args.queryid, 'ldbc_snb_grblas')
    except ModuleNotFoundError:
        # todo
        print("give query id (%d) not found." % args.queryid)
        return

    query.calc(args.datadir, *args.params)


if __name__ == '__main__':
    execute()
