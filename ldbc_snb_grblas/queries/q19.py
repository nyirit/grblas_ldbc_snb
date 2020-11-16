"""
LDBC SNB BI query 19. Interaction path between cities
https://ldbc.github.io/ldbc_snb_docs_snapshot/bi-read-19.pdf
"""
from itertools import repeat

from grblas import dtypes, semiring
from grblas.mask import StructuralMask
from grblas.matrix import Matrix
from grblas.ops import UnaryOp

from ldbc_snb_grblas.loader import Loader
from ldbc_snb_grblas.logger import Logger


def calc(data_dir, city1_id, city2_id):
    city1_id = int(city1_id)
    city2_id = int(city2_id)

    # init timer
    logger = Logger()

    # load vertices
    loader = Loader(data_dir)

    persons = loader.load_empty_vertex('person')
    places = loader.load_empty_vertex('place')
    comments = loader.load_empty_vertex('comment')
    posts = loader.load_empty_vertex('post')

    city1_index = places.id2index(city1_id)
    city2_index = places.id2index(city2_id)

    # print("Vertices loaded\t%s" % logger.get_total_time(), file=stderr)

    # load edges
    person_knows_person = loader.load_edge(persons, 'knows', persons, is_dynamic=True, undirected=True,
                                           from_id_header_override='Person1.id', to_id_header_override='Person2.id')
    person_locatedin_city = loader.load_edge(persons, 'isLocatedIn', places, is_dynamic=True,
                                             rmask={city1_index, city2_index})

    persons_in_city1, _ = person_locatedin_city[:, city1_index].new().to_values()
    persons_in_city2, _ = person_locatedin_city[:, city2_index].new().to_values()

    # create a matrix containing message-hascreator-person relation, which contains both posts and comments
    # fixme: does it worth at all to create these message-hascreator and replyof-message matrices...?
    # fixme: This could be solved by multiplying them separately.
    comment_hascreator_person = loader.load_edge(comments, 'hasCreator', persons, is_dynamic=True)
    post_hascreator_person = loader.load_edge(posts, 'hasCreator', persons, is_dynamic=True)

    # make sure to have the same person dimension length
    person_knows_person.resize(persons.length, persons.length)
    comment_hascreator_person.resize(comment_hascreator_person.nrows, persons.length)
    post_hascreator_person.resize(post_hascreator_person.nrows, persons.length)

    message_hascreator_person = comment_hascreator_person.dup()
    message_hascreator_person.resize(comments.length + posts.length, persons.length)
    message_hascreator_person[comments.length:comments.length + posts.length, :] = post_hascreator_person

    # create a matrix containing comment-replyOf-message relation, which contains both posts and comments as parents
    comment_replyof_comment = loader.load_edge(comments, 'replyOf', comments, is_dynamic=True, to_id_header_override='ParentComment.id')
    comment_replyof_post = loader.load_edge(comments, 'replyOf', posts, is_dynamic=True, to_id_header_override='ParentPost.id')
    comment_replyof_messge = comment_replyof_comment.dup()
    comment_replyof_messge.resize(comments.length, comments.length + posts.length)
    comment_replyof_messge[:, comments.length:comments.length + posts.length] = comment_replyof_post

    logger.loading_finished()

    # calculate weight matrix
    person_replyof_message = message_hascreator_person.T.mxm(comment_replyof_messge.T).new()
    person_weight_person = person_replyof_message.mxm(comment_hascreator_person).new(dtype=dtypes.FP32, mask=StructuralMask(person_knows_person))

    # make sure we have a square matrix. It can be different because not all person created replies or comments.
    person_weight_person.resize(persons.length, persons.length)

    # make weight matrix bidirectional
    person_weight_person << person_weight_person.ewise_add(person_weight_person.T)

    recipr = UnaryOp.register_anonymous(lambda x: 1/x)
    person_weight_person << person_weight_person.apply(recipr)

    # calculate shortest path on person_weight_person using Floyd-Warshall alg.
    # set diagonal to 0
    for i in range(person_weight_person.ncols):
        person_weight_person[i, i] << 0

    # Batched Bellman-Ford algorith for finding shortest path
    len_city1 = len(persons_in_city1)
    path_matrix = Matrix.from_values(range(len_city1), persons_in_city1, repeat(0, len_city1),
                                     ncols=persons.length, dtype=person_weight_person.dtype)

    prev_path_matrix = path_matrix.dup()
    while True:
        path_matrix << path_matrix.mxm(person_weight_person, op=semiring.min_plus)

        if path_matrix.isequal(prev_path_matrix):
            # break if a fix point is reached
            break

        prev_path_matrix = path_matrix.dup()

    # extract only people in city 2
    results = path_matrix[:, list(persons_in_city2)].new()

    result_tuples = [
        (persons.index2id(persons_in_city1[p1]), persons.index2id(persons_in_city2[p2]), w)
        for p1, p2, w in zip(*results.to_values())
    ]

    # sort and print results
    # print("Result extracted, sorting...\t%s" % logger.get_total_time(), file=stderr)
    result_tuples = sorted(result_tuples, key=lambda x: (-x[2], x[0], x[1]))

    logger.calculation_finished()

    for pair in result_tuples:
        print(*pair)

    # print("All done!\t%s" % logger.get_total_time(), file=stderr)
