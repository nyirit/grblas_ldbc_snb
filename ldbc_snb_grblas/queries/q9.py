"""
LDBC SNB BI query 9. Top thread initiators
https://ldbc.github.io/ldbc_snb_docs_snapshot/bi-read-09.pdf
"""

from itertools import islice

from ldbc_snb_grblas.loader import Loader
from ldbc_snb_grblas.logger import Logger
from ldbc_snb_grblas.util import parse_user_date, get_date_mask


def calc(data_dir, start_date, end_date):
    try:
        start_date = parse_user_date(start_date)
        end_date = parse_user_date(end_date)
    except ValueError as e:
        # todo
        print("Invalid date parameter: %s" % e)
        return

    # init timer
    logger = Logger()

    loader = Loader(data_dir)
    persons = loader.load_vertex('person', is_dynamic=True, column_names=['firstName', 'lastName'])
    comments = loader.load_vertex('comment', is_dynamic=True, column_names=['creationDate'])
    posts = loader.load_vertex('post', is_dynamic=True, column_names=['creationDate'])

    # print("Vertices loaded\t%s" % logger.get_total_time(), file=stderr)

    # get masks
    comments_mask = get_date_mask(comments, 0, start_date, end_date)
    posts_mask = get_date_mask(posts, 0, start_date, end_date)

    # print("Edge masks calculated\t%s" % logger.get_total_time(), file=stderr)

    post_hascreator_person = loader.load_edge(posts, 'hasCreator', persons, is_dynamic=True, lmask=posts_mask)
    comment_replyof_post = loader.load_edge(comments, 'replyOf', posts, is_dynamic=True, lmask=comments_mask,
                                            rmask=posts_mask, to_id_header_override='ParentPost.id')
    comment_replyof_comment = loader.load_edge(comments, 'replyOf', comments, is_dynamic=True, lmask=comments_mask,
                                               rmask=comments_mask, to_id_header_override='ParentComment.id')

    # print("Edges loaded\t%s" % logger.get_total_time(), file=stderr)

    logger.loading_finished()

    # get number of posts (initiated threads) per persons
    thread_count = post_hascreator_person.reduce_columns().new()

    # get direct replies for each post as a person-comment matrix
    m_person_comment = post_hascreator_person.T.mxm(comment_replyof_post.T).new()

    # calculate number of direct comments for persons
    vec_person = thread_count.ewise_add(m_person_comment.reduce_rows().new()).new()

    # get all comments iteratively per person
    while m_person_comment.nvals > 0:
        # get next comments
        m_person_comment << m_person_comment.mxm(comment_replyof_comment.T)

        # accumulate results
        vec_person << vec_person.ewise_add(m_person_comment.reduce_rows().new())

    # print("Data calculated\t%s" % logger.get_total_time(), file=stderr)

    # sort results by message_count
    sorted_result = sorted(zip(*vec_person.to_values()), key=lambda x: (-x[1], persons.index2id(x[0])))  # fixme

    # print("Data sorted\t%s" % logger.get_total_time(), file=stderr)

    logger.calculation_finished()

    # print results
    for person_index, message_count in islice(sorted_result, 100):
        first_name = persons.data[person_index][0]
        last_name = persons.data[person_index][1]
        person_id = persons.index2id(person_index)
        print(person_id, first_name, last_name, thread_count[person_index].value, message_count)

    # print("All done\t%s" % logger.get_total_time(), file=stderr)
