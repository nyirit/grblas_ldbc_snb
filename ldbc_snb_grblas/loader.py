import csv
import errno

from grblas import dtypes
from itertools import repeat

import logging
from os import strerror
from os import path

from grblas.matrix import Matrix


class LoadError(Exception):  # fixme
    pass


class VertexType:
    def __init__(self, name, index2id=None, id2index=None, data=None, length=0):
        self.name = name
        self._index2id = index2id or []
        self._id2index = id2index or {}
        self.data = data or []
        self.length = length
        self.index_data_dict = None

    def index2id(self, index):
        # the index should already be present in the mapping, if not, it was not loaded or used before,
        # so it doesn't make any sense to translate it to an id.
        return self._index2id[index]

    def id2index(self, oid, auto_create=True):
        # if an id wasn't loaded, let's create the mapping on-the-fly
        # this is useful when edges are used without needing any property for the corresponding vertices
        if oid not in self._id2index:
            if auto_create:
                self._id2index[oid] = self.length
                self._index2id.append(oid)
                self.length += 1
            else:
                return None

        return self._id2index[oid]

    def get_index_data_dict(self):
        """

        :return:
        """

        if not self.data:
            raise ValueError(f"Cannot return dictiory for {self.name} vertex, because there's no data elements loaded.")

        if self.index_data_dict is None:
            result = dict()
            for i in range(self.length):
                result[i] = self.data[i]
            self.index_data_dict = result

        return self.index_data_dict


logger = logging.getLogger(__name__)

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

        # make sure all header elements are lowercase
        header = [x.split(':')[0].lower() for x in header]

        for name in column_names:
            # make sure column name is lowercase as well
            name = name.lower()

            try:
                index = header.index(name)
                columns.append(index)

                # Delete content for this header as it should not be found again.
                # The possibility for finding it again exists, as e.g. comment<-replyOf-comment relation has
                # Comment.id twice in the header.
                header[index] = ''
            except (AttributeError, ValueError):
                logger.error("Column '%s' not found! Possible values are: %s" % (
                    name, ', '.join(header)))
                raise LoadError()

        return columns

    def load_vertex(self, vertex_type_name: str, column_names=None, *, is_dynamic, id_mask=None):
        """

        :param vertex_type_name:
        :param column_names:
        :param is_dynamic:
        :return:
        """
        filename = "%s%s" % (vertex_type_name, self.filename_suffix)
        subdir = 'dynamic' if is_dynamic else 'static'
        file_path = path.join(self.data_dir, subdir, filename)

        column_names = column_names or []

        with open(file_path) as csvfile:
            reader = csv.reader(csvfile, delimiter=DEFAULT_DELIMITER, quotechar=DEFAULT_QUOTE)

            header = next(reader)

            # determine index of all needed fields, and add index as well
            column_names.insert(0, ID_NAME)
            columns = self._parse_header(header, column_names)

            mapping = []  # logical (dense) id -> original (sparse) id
            reverse_mapping = {}  # original id -> logical id
            data = []  # any additional data based on 'column_names'

            for i, row in enumerate(reader):
                row_data = [row[i] for i in columns]
                row_id = int(row_data.pop(0))

                if id_mask is not None and row_id not in id_mask:
                    continue

                mapping.append(row_id)
                reverse_mapping[row_id] = i

                # if there's anything else to store
                if row_data:
                    data.append(row_data)

            return VertexType(vertex_type_name, mapping, reverse_mapping, data, len(mapping))

    @staticmethod
    def load_empty_vertex(vertex_type_name: str):
        """
        Creates a VertexType without any data or id mapping.
        This is useful when only the edges are interesting not the actual vertex data.

        Note: the vertex_type_name is not validated in any way.
        """
        return VertexType(vertex_type_name)

    def load_edge(self, from_vertex_type: VertexType, edge_name: str, to_vertex_type: VertexType,
                  *, is_dynamic: bool, dtype=dtypes.INT32, lmask=None, rmask=None, undirected=False,
                  from_id_header_override=None, to_id_header_override=None):
        """
        Loads edges between of type 'edge_name' between 'from_vertex_type' and 'to_vertex_type'. These parameters
        also define the csv file that will be loaded.

        When using rmask or rmask not all entries will be loaded only the ones that have an index (and not id!)
        already present in the mask tuple. This method assumes that the corresponding id should already be present
        in the mapping. This results in matrix dimensions that correspond to the number of matching elements,
        instead of the number of all elements. i.e. if only 1 entry matches the lmask out of a 1000, the matrix will
        only have 1 row instead of 1000.

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
            raise LoadError("(%s)-[:%s]-(%s) connection doesn't exist." % (from_vertex_type.name, edge_name, to_vertex_type.name))

        with open(file_path) as csvfile:
            reader = csv.reader(csvfile, delimiter=DEFAULT_DELIMITER, quotechar=DEFAULT_QUOTE)

            # get id columns
            # todo: if attributes are needed, column_names should be a function parameter and
            # todo: these values should be inserted into that
            column_names = [
                from_id_header_override or f'{from_vertex_type.name}.id',
                to_id_header_override or f'{to_vertex_type.name}.id',
            ]

            header = next(reader)
            columns = self._parse_header(header, column_names)

            from_indexes = []
            to_indexes = []

            for i, row in enumerate(reader):
                row_data = [row[i] for i in columns]
                id_from = int(row_data.pop(0))
                id_to = int(row_data.pop(0))

                from_index = None
                if lmask is not None:
                    # if a mask is present auto creation of mapping doesn't make sense, because the mask already
                    # assumes an index-id mapping
                    from_index = from_vertex_type.id2index(id_from, auto_create=False)
                    if from_index is None or from_index not in lmask:
                        continue

                to_index = None
                if rmask is not None:
                    # if a mask is present auto creation of mapping doesn't make sense, because the mask already
                    # assumes an index-id mapping
                    to_index = to_vertex_type.id2index(id_to, auto_create=False)
                    if to_index is None or to_index not in rmask:
                        continue

                # because of the auto_create=False, at this point to_index and/or from_index may be None.
                # let's make sure they are valid.
                to_index = to_index or to_vertex_type.id2index(id_to, auto_create=True)
                from_index = from_index or from_vertex_type.id2index(id_from, auto_create=True)

                from_indexes.append(from_index)
                to_indexes.append(to_index)

                # if there's anything else to store
                if row_data:
                    # todo: save additional properties connected to the edge.
                    pass

        m = Matrix.from_values(from_indexes, to_indexes,
                               repeat(1, len(from_indexes)),  # 1 for all value
                               nrows=from_vertex_type.length,
                               ncols=to_vertex_type.length,
                               dtype=dtype,
                               name="%s_%s_%s" % (from_vertex_type.name, edge_name, to_vertex_type.name))

        if undirected:
            m << m.ewise_add(m.T)

        return m
