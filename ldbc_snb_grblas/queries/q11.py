"""
LDBC SNB BI query 11. Friend triangles
https://ldbc.github.io/ldbc_snb_docs_snapshot/bi-read-11.pdf
"""

from itertools import repeat

from grblas.matrix import Matrix
from grblas.vector import Vector

from ldbc_snb_grblas.loader import Loader
from ldbc_snb_grblas.logger import Logger


def calc(data_dir, country_name):
    # init timer
    logger = Logger()

    # load vertices
    loader = Loader(data_dir)

    persons = loader.load_empty_vertex('person')
    places = loader.load_vertex('place', is_dynamic=False, column_names=['name', 'type'])

    # print("Vertices persons and places\t%s" % logger.get_total_time(), file=stderr)

    # load edges
    person_locatedin_place = loader.load_edge(persons, 'isLocatedIn', places, is_dynamic=True)
    place_ispartof_place = loader.load_edge(places, 'isPartOf', places, is_dynamic=False)
    # print("Loaded locatedIn and isPartOf edges\t%s" % logger.get_total_time(), file=stderr)

    # get country index
    country_index = places.data.index([country_name, 'country'])
    country_vector = Vector.from_values([country_index], [True], size=place_ispartof_place.ncols)

    # cities mapped to original ids
    country_vector_indices, _ = country_vector.vxm(place_ispartof_place.T).new().to_values()
    country_city_matrix = Matrix.from_values(country_vector_indices, country_vector_indices, repeat(1, len(country_vector_indices)), nrows=places.length, ncols=persons.length)
    person_mask, _ = person_locatedin_place.mxm(country_city_matrix).new().reduce_rows().new().to_values()
    person_mask = set(person_mask)

    # print("Created person mask\t%s" % logger.get_total_time(), file=stderr)

    # load person-knows-person for people located in 'country'
    person_knows_person = loader.load_edge(persons, 'knows', persons, is_dynamic=True, lmask=person_mask, rmask=person_mask, undirected=True)

    logger.loading_finished()

    # calculate triangles
    r = person_knows_person.mxm(person_knows_person).new()
    r << r.ewise_mult(person_knows_person)
    triangle_count = r.reduce_rows().new().reduce().new().value // 6

    logger.calculation_finished()
    # print("Triangles calculated. All done\t%s" % logger.get_total_time(), file=stderr)

    print(triangle_count)
