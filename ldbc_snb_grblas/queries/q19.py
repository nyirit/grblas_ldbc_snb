from sys import stderr
from time import perf_counter

from grblas import dtypes, semiring, monoid
from grblas.matrix import Matrix
from grblas.ops import UnaryOp

from ldbc_snb_grblas.loader import Loader


def calc(data_dir, city1_id, city2_id):
    city1_id = int(city1_id)
    city2_id = int(city2_id)

    time_start = perf_counter()

    # load vertices
    loader = Loader(data_dir)

    persons = loader.load_empty_vertex('person')
    places = loader.load_empty_vertex('place')
    comments = loader.load_empty_vertex('comment')
    posts = loader.load_empty_vertex('post')

    city1_index = places.id2index(city1_id)
    city2_index = places.id2index(city2_id)

    print("Vertices loaded\t%s" % (perf_counter() - time_start), file=stderr)

    # load edges
    person_locatedin_city = loader.load_edge_type(persons, 'isLocatedIn', places, is_dynamic=True,
                                                  rmask={city1_index, city2_index})

    persons_in_city1, _ = person_locatedin_city[:, city1_index].new().to_values()
    persons_in_city2, _ = person_locatedin_city[:, city2_index].new().to_values()

    # create a matrix containing message-hascreator-person relation, which contains both posts and comments
    # fixme: does it worth at all to create these message-hascreator and replyof-message matrices...?
    # fixme: This could be solved by multiplying them separately.
    comment_hascreator_person = loader.load_edge_type(comments, 'hasCreator', persons, is_dynamic=True)
    post_hascreator_person = loader.load_edge_type(posts, 'hasCreator', persons, is_dynamic=True)

    message_hascreator_person = comment_hascreator_person.dup()
    message_hascreator_person.resize(comments.length + posts.length, persons.length)
    message_hascreator_person[comments.length:comments.length + posts.length, :] = post_hascreator_person

    # create a matrix containing comment-replyOf-message relation, which contains both posts and comments as parents
    comment_replyof_comment = loader.load_edge_type(comments, 'replyOf', comments, is_dynamic=True)
    comment_replyof_post = loader.load_edge_type(comments, 'replyOf', posts, is_dynamic=True)
    comment_replyof_messge = comment_replyof_comment.dup()
    comment_replyof_messge.resize(comments.length, comments.length + posts.length)
    comment_replyof_messge[:, comments.length:comments.length + posts.length] = comment_replyof_post

    print("Edges loaded\t%s" % (perf_counter() - time_start), file=stderr)

    # calculate weight matrix
    person_replyof_message = comment_hascreator_person.T.mxm(comment_replyof_messge).new()
    person_weight_person = person_replyof_message.mxm(message_hascreator_person).new(dtype=dtypes.FP32)

    # make weight matrix bidirectional
    person_weight_person << person_weight_person.ewise_add(person_weight_person.T)

    recipr = UnaryOp.register_anonymous(lambda x: 1/x)
    person_weight_person << person_weight_person.apply(recipr)

    print("Weight matrix calculated\t%s" % (perf_counter() - time_start), file=stderr)

    # calculate shortest path on person_weight_person using Floyd-Warshall alg.

    # set diagonal to 0
    for i in range(person_weight_person.ncols):
        person_weight_person[i, i] << 0

    # create a 1-column-matrix and b 1-row-matrix
    a = Matrix.new(dtype=person_weight_person.dtype, nrows=person_weight_person.nrows, ncols=1)
    b = Matrix.new(dtype=person_weight_person.dtype, nrows=1, ncols=person_weight_person.ncols)
    for k in range(person_weight_person.ncols):
        # extract given row and column
        a[:, 0] << person_weight_person[:, k].new()
        b[0, :] << person_weight_person[k, :].new()

        # calculate path using the new vertex
        tmp = a.mxm(b, op=semiring.min_plus).new()

        # save the minimum of the currently and previously calculated values for each vertex
        person_weight_person << person_weight_person.ewise_add(tmp, op=monoid.min)

    print("Shortest paths calculated\t%s" % (perf_counter() - time_start), file=stderr)

    # extract results and map them to a list of tuples
    results = person_weight_person[list(persons_in_city1), list(persons_in_city2)].new()

    result_tuples = []
    for i in range(len(persons_in_city1)):
        person1_id = persons.index2id(persons_in_city1[i])

        for j in range(len(persons_in_city2)):
            person2_id = persons.index2id(persons_in_city2[j])
            weight = results[i, j].value
            result_tuples.append((person1_id, person2_id, weight))

    # sort and print results
    print("Result extracted, sorting...\t%s" % (perf_counter() - time_start), file=stderr)
    result_tuples = sorted(result_tuples, key=lambda x: (-x[2], x[1]))

    for pair in result_tuples:
        print(*pair)

    print("All done!\t%s" % (perf_counter() - time_start), file=stderr)
