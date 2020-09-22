from itertools import repeat
from sys import stderr
from time import perf_counter

from grblas.matrix import Matrix
from grblas.vector import Vector

from ldbc_snb_grblas.loader import Loader


def calc(data_dir, country_name):
    time_start = perf_counter()

    # load vertices
    loader = Loader(data_dir)

    # todo: persons are not really needed here. They are only loaded to create the mappings. This could be done
    # todo: on the fly while loading the edges.
    persons = loader.load_vertex_type('person', is_dynamic=True)
    places = loader.load_vertex_type('place', is_dynamic=False, column_names=['name', 'type'])

    print("Vertices persons and places\t%s" % (perf_counter() - time_start), file=stderr)

    # load edges
    person_locatedin_place = loader.load_edge_type(persons, 'isLocatedIn', places, is_dynamic=True)
    place_ispartof_place = loader.load_edge_type(places, 'isPartOf', places, is_dynamic=False)
    print("Loaded locatedIn and isPartOf edges\t%s" % (perf_counter() - time_start), file=stderr)

    # get country index
    country_index = places.data.index([country_name, 'country'])
    country_vector = Vector.from_values([country_index], [True], size=place_ispartof_place.ncols)

    # cities mapped to original ids
    country_vector_indices, _ = country_vector.vxm(place_ispartof_place.T).new().to_values()
    country_city_matrix = Matrix.from_values(country_vector_indices, country_vector_indices, repeat(1, len(country_vector_indices)), nrows=places.length, ncols=persons.length)
    person_mask, _ = person_locatedin_place.mxm(country_city_matrix).new().reduce_rows().new().to_values()
    person_mask = set(person_mask)

    print("Created person mask\t%s" % (perf_counter() - time_start), file=stderr)

    # load person-knows-person for people located in 'country'
    person_knows_person = loader.load_edge_type(persons, 'knows', persons, is_dynamic=True, lmask=person_mask, rmask=person_mask)

    # make edges undirected
    person_knows_person << person_knows_person.ewise_add(person_knows_person.T)

    # calculate triangles
    r = person_knows_person.mxm(person_knows_person).new()
    r << r.ewise_mult(person_knows_person)
    triangle_count = r.reduce_rows().new().reduce().new().value // 6

    print("Triangles calculated. All done\t%s" % (perf_counter() - time_start), file=stderr)

    print(triangle_count)

