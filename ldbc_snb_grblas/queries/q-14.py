"""
Legacy LDBC SNB BI query 14. Top thread initiator
https://arxiv.org/pdf/2001.02299.pdf#page=69

Note: in the newer version of LDBC SNB BI this query is omitted.
      That is why the filename is -14 instead of 14.
"""

from itertools import islice

from ldbc_snb_grblas.loader import Loader
from ldbc_snb_grblas.logger import Logger
from ldbc_snb_grblas.util import parse_user_date, get_date_mask

result_limit = 100


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

    # load vertices
    loader = Loader(data_dir)

    persons = loader.load_vertex('person', column_names=['firstName', 'lastName'], is_dynamic=True)
    posts = loader.load_vertex('post', column_names=['creationDate'], is_dynamic=True)
    comments = loader.load_vertex('comment', column_names=['creationDate'], is_dynamic=True)

    # print("Vertices loaded\t%s" % logger.get_total_time(), file=stderr)

    post_hascreator_person = loader.load_edge(posts, 'hasCreator', persons, is_dynamic=True)
    comment_replyof_post = loader.load_edge(comments, 'replyOf', posts, is_dynamic=True, to_id_header_override='ParentPost.id')
    comment_replyof_comment = loader.load_edge(comments, 'replyOf', comments, is_dynamic=True, to_id_header_override='ParentComment.id')

    # print("Edges loaded\t%s" % logger.get_total_time(), file=stderr)
    logger.loading_finished()

    # get masks
    comments_mask = get_date_mask(comments, 0, start_date, end_date)
    posts_mask = get_date_mask(posts, 0, start_date, end_date)

    # print("Edge masks calculated\t%s" % logger.get_total_time(), file=stderr)

    # calculate post (=thread) count for each person
    masked_post_hascreator_person = post_hascreator_person[posts_mask, :].new()
    thread_count = masked_post_hascreator_person.reduce_columns().new()

    # print("Thread counts calculated\t%s" % logger.get_total_time(), file=stderr)

    # calculate transitive reply tree for each post
    replies = comment_replyof_post[comments_mask, posts_mask].new().T.new()
    front = replies.dup()

    masked_comment_replyof_comment = comment_replyof_comment[comments_mask, comments_mask].new()
    while True:
        front << front.mxm(masked_comment_replyof_comment.T)

        if not front.nvals:
            break

        replies << replies.ewise_add(front)

    # reduce to get number of replies per post
    replies_per_post = replies.reduce_rows().new()

    # join hasCreator, to get replies per person
    replies_per_person = replies_per_post.vxm(masked_post_hascreator_person).new()
    replies_per_person = dict(zip(*replies_per_person.to_values()))

    # print("Replies calculated\t%s" % logger.get_total_time(), file=stderr)

    # create list of (person_id, person_index, thread_count, message_count),
    # where message count equals to thread count + transitive replies count
    result = map(lambda x: (persons.index2id(x[0]), x[0], x[1], x[1] + replies_per_person.get(x[0], 0)),
                 zip(*thread_count.to_values()))

    # sort by replies dsc, person id asc
    sorted_result = sorted(result, key=lambda x: (-x[3], x[0]))
    # print("Data sorted\t%s" % logger.get_total_time(), file=stderr)

    # get person data as dictiory to produce first and last names
    persons_data = persons.get_index_data_dict()

    logger.calculation_finished()

    for pid, pindex, threads, message_count in islice(sorted_result, result_limit):
        first_name, last_name = persons_data[pindex]
        print(f"{pid};{first_name};{last_name};{threads};{message_count}")

    # print("All done\t%s" % logger.get_total_time(), file=stderr)
    logger.print_finished()
