import csv
import errno
from os import strerror
from os import path


class Loader:
    def __init__(self, data_dir, filename_suffix="_0_0.csv"):
        """

        :param data_dir:
        """
        if not path.isdir(data_dir):
            raise FileNotFoundError(errno.ENOENT, strerror(errno.ENOENT), data_dir)

        self.data_dir = data_dir
        self.filename_suffix = filename_suffix

    def load_vertex(self, vertex_name):
        """

        :param vertex_name:
        :return:
        """
        raise NotImplementedError()

    def load_edge(self, from_vertex, edge_name, to_vertex, *, is_dynamic):
        """

        :param edge_name:
        :param from_vertex:
        :param to_vertex:
        :return:
        """

        filename = "%s_%s_%s%s" % (from_vertex, edge_name, to_vertex, self.filename_suffix)
        subdir = 'dynamic' if is_dynamic else 'static'
        full_path = path.join(self.data_dir, subdir, filename)

        if not path.isfile(full_path):
            pass

        with open(full_path) as csvfile:
            reader = csv.reader(csvfile, delimiter='|', quotechar='"')

            # skip header
            next(reader)

            for row in reader:
                pass
