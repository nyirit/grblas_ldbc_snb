from itertools import repeat, islice
from sys import stderr
from time import perf_counter

from grblas.mask import StructuralMask
from grblas.matrix import Matrix
from grblas.vector import Vector

from ldbc_snb_grblas.loader import Loader


def calc(data_dir, person_id, tag_name):
    person_id = int(person_id)

    time_start = perf_counter()

    # load vertices
    loader = Loader(data_dir)

    persons = loader.load_vertex_type('person', is_dynamic=True)
    person_vector = Vector.from_values([persons.id2index(person_id)], [True], size=persons.length)

    tags = loader.load_vertex_type('tag', is_dynamic=False, column_names=['name'])

    tag_index = tags.data.index([tag_name])
    tag_vector = Vector.from_values([tag_index], [True], size=tags.length)

    print("Vertices loaded\t%s" % (perf_counter() - time_start), file=stderr)

    # load edges
    person_knows_person = loader.load_edge_type(persons, 'knows', persons, is_dynamic=True, undirected=True)

    person_hasinterest_tag = loader.load_edge_type(persons, 'hasInterest', tags, is_dynamic=True)

    print("Edges loaded\t%s" % (perf_counter() - time_start), file=stderr)

    # direct friends of given person
    friendsl1 = person_vector.vxm(person_knows_person).new()

    # get second level friends of given person, who are interested in given tag. (They should not be in friendsl1!)
    interested_persons = tag_vector.vxm(person_hasinterest_tag.T).new(mask=~StructuralMask(friendsl1))

    # manually remove the parameter person as he is interested in the given tag and is a friend of his friends
    del interested_persons[persons.id2index(person_id)]

    friendsl2 = friendsl1.vxm(person_knows_person).new(mask=StructuralMask(interested_persons))
    friendsl2_keys, _ = friendsl2.to_values()

    # calculate mutual friend count...
    # result_matrix start out as selection matrix for level2 friends
    result_matrix = Matrix.from_values(friendsl2_keys, friendsl2_keys,
                                       values=repeat(1, friendsl2.nvals),
                                       nrows=persons.length,
                                       ncols=persons.length)

    # get the corresponding friends for each level2 friend
    result_matrix << result_matrix.mxm(person_knows_person)

    # create a selection matrix for level1 friends
    friendsl1_keys, _ = friendsl1.to_values()
    friendsl1_matrix = Matrix.from_values(friendsl1_keys, friendsl1_keys,
                                          values=repeat(1, friendsl1.nvals),
                                          nrows=persons.length,
                                          ncols=persons.length)

    # filter for level1 friends (so we will have the mutual friends)
    result_matrix << result_matrix.mxm(friendsl1_matrix)

    # reduce rows to get count of mutual friends for each person and
    # create (person_index, count) tuples
    result_values = zip(*result_matrix.reduce_rows().new().to_values())

    # create final (person_id, count) tuples and sort them by count ASC, id DESC
    result = sorted(map(lambda x: (persons.index2id(x[0]), x[1]), result_values), key=lambda x: (-x[1], x[0]))

    # print top results
    for person_id, mutual_friend_count in islice(result, 20):
        print(person_id, mutual_friend_count)

    print("All done\t%s" % (perf_counter() - time_start), file=stderr)
