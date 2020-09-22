import csv
import errno

from grblas import dtypes
from itertools import repeat

import logging
from collections import namedtuple
from os import strerror
from os import path

from grblas.matrix import Matrix


class LoadError(Exception):  # fixme
    pass


logger = logging.getLogger(__name__)

VertexType = namedtuple('VertexType', [
    'name',
    'index2id',  # logical (dense) id -> original (sparse) id
    'id2index',  # original (sparse) id -> logical (dense) id
    'data',
    'length'  # nr. of vertices present
])


DEFAULT_DELIMITER = '|'
DEFAULT_QUOTE = '"'

ID_NAME = 'id'


class Loader:
    def __init__(self, data_dir, filename_suffix="_0_0.csv"):
        """

        :param data_dir:
        """
        if not path.isdir(data_dir):
            raise FileNotFoundError(errno.ENOENT, strerror(errno.ENOENT), data_dir)

        self.data_dir = data_dir
        self.filename_suffix = filename_suffix

    def _parse_header(self, header, column_names):
        """
        Gets index for columns based on the header.
        :param header: list of header string values.
        :param column_names: list of string values that are needed.
        :return: list of indexes of needed values in header.
        """
        columns = []

        for name in column_names:
            try:
                index = header.index(name)
                columns.append(index)

                # Delete content for this header as it should not be found again.
                # The possibility for finding it again exists, as e.g. comment<-replyOf-comment relation has
                # Comment.id twice in the header.
                header[index] = ''
            except AttributeError:
                logger.error("Column '%s' not found! Possible values are: %s" % (
                    name, ', '.join(header)))
                raise LoadError()

        return columns

    def load_vertex_type(self, vertex_type_name: str, column_names=[], *, is_dynamic):
        """

        :param vertex_type_name:
        :param column_names:
        :param is_dynamic:
        :return:
        """
        filename = "%s%s" % (vertex_type_name, self.filename_suffix)
        subdir = 'dynamic' if is_dynamic else 'static'
        file_path = path.join(self.data_dir, subdir, filename)

        with open(file_path) as csvfile:
            reader = csv.reader(csvfile, delimiter=DEFAULT_DELIMITER, quotechar=DEFAULT_QUOTE)

            header = next(reader)

            # determine index of all needed fields, and add index as well
            column_names.insert(0, ID_NAME)
            columns = self._parse_header(header, column_names)

            mapping = []  # logical (dense) id -> original (sparse) id
            revese_mapping = {}  # original id -> logical id
            data = []  # any additional data based on 'column_names'

            for i, row in enumerate(reader):
                row_data = [row[i] for i in columns]
                index = int(row_data.pop(0))
                mapping.append(index)
                revese_mapping[index] = i

                # if there's anything else to store
                if row_data:
                    data.append(row_data)

            return VertexType(vertex_type_name, mapping, revese_mapping, data, len(mapping))

    def load_edge_type(self, from_vertex_type: VertexType, edge_name: str, to_vertex_type: VertexType,
                       *, is_dynamic: bool, dtype=dtypes.INT32, lmask=None, rmask=None):
        """

        TODO: add parsing of properties of a relation.
        :param edge_name:
        :param from_vertex_type:
        :param to_vertex_type:
        :param is_dynamic:
        :return: adjacency matrix
        """

        # concat full filename for input file
        filename = "%s_%s_%s%s" % (from_vertex_type.name, edge_name, to_vertex_type.name, self.filename_suffix)

        # concat file path
        subdir = 'dynamic' if is_dynamic else 'static'
        file_path = path.join(self.data_dir, subdir, filename)

        if not path.isfile(file_path):
            pass  # fixme should we handle this...? open() will raise an exception...

        with open(file_path) as csvfile:
            reader = csv.reader(csvfile, delimiter=DEFAULT_DELIMITER, quotechar=DEFAULT_QUOTE)

            # get id columns
            # todo: if attributes are needed, column_names should be a function parameter and
            # todo: these values should be inserted into that
            column_names = [
                '%s.id' % from_vertex_type.name.title(),
                '%s.id' % to_vertex_type.name.title(),
            ]

            header = next(reader)
            columns = self._parse_header(header, column_names)

            from_indexes = []
            to_indexes = []

            for i, row in enumerate(reader):
                row_data = [row[i] for i in columns]
                id_from = int(row_data.pop(0))
                id_to = int(row_data.pop(0))

                # check if both sides of the connection is present
                if (id_from not in from_vertex_type.id2index or
                        id_to not in to_vertex_type.id2index):
                    logger.error("Dropping dangling edge: (%s:%s)-[%s]-(%s:%s)" % (
                        from_vertex_type.name, id_from, edge_name, to_vertex_type.name, id_to
                    ))
                    continue

                from_index = from_vertex_type.id2index[id_from]
                if lmask is not None and from_index not in lmask:
                    continue

                to_index = to_vertex_type.id2index[id_to]
                if rmask is not None and to_index not in rmask:
                    continue

                from_indexes.append(from_index)
                to_indexes.append(to_index)

                # if there's anything else to store
                if row_data:
                    # todo: save additional properties
                    pass

        m = Matrix.from_values(from_indexes, to_indexes,
                               repeat(1, len(from_indexes)),  # True for all value
                               nrows=len(from_vertex_type.index2id),
                               ncols=len(to_vertex_type.index2id),
                               dtype=dtype,
                               name="%s_%s_%s" % (from_vertex_type.name, edge_name, to_vertex_type.name))

        return m
