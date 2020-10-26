"""
LDBC SNB BI query 5. Most active posters of a given topic
https://ldbc.github.io/ldbc_snb_docs_snapshot/bi-read-05.pdf
"""
from itertools import islice

from grblas.mask import StructuralMask
from grblas.ops import UnaryOp

from ldbc_snb_grblas.grutil import merge_matrix
from ldbc_snb_grblas.loader import Loader
from ldbc_snb_grblas.logger import Logger

points_per_like = 10
points_per_reply = 2
result_limit = 100


def calc(data_dir, tag_name):
    # init timer
    logger = Logger()

    # load vertices
    loader = Loader(data_dir)
    tags = loader.load_vertex('tag', column_names=['name'], is_dynamic=False)

    # todo: cannot empty load persons right now,
    # todo: because then person_likes_comment and person_likes_post won't match dimensions.
    persons = loader.load_vertex('person', is_dynamic=True)
    comments = loader.load_empty_vertex('comment')
    posts = loader.load_empty_vertex('post')

    # print("Vertices loaded\t%s" % logger.get_total_time(), file=stderr)

    # load edges

    # todo: masks could be used while loading in order to load only those messages/likes that are
    # todo: connected to messages which have the given tag

    # due to not loading the comments and pots separately, first the hascreator edges have to be loaded
    # to have a complete id-index mapping.
    comment_hascreator_person = loader.load_edge(comments, 'hasCreator', persons, is_dynamic=True)
    post_hascreator_person = loader.load_edge(posts, 'hasCreator', persons, is_dynamic=True)

    comment_hastag_tag = loader.load_edge(comments, 'hasTag', tags, is_dynamic=True)
    post_hastag_tag = loader.load_edge(posts, 'hasTag', tags, is_dynamic=True)
    comment_replyof_post = loader.load_edge(comments, 'replyOf', posts, is_dynamic=True, to_id_header_override='ParentPost.id')
    comment_replyof_comment = loader.load_edge(comments, 'replyOf', comments, is_dynamic=True, to_id_header_override='ParentComment.id')
    person_likes_comment = loader.load_edge(persons, 'likes', comments, is_dynamic=True)
    person_likes_post = loader.load_edge(persons, 'likes', posts, is_dynamic=True)

    # print("Edges loaded\t%s" % logger.get_total_time(), file=stderr)
    logger.loading_finished()

    # create message matrices
    comment_replyof_message = merge_matrix(comment_replyof_comment, comment_replyof_post, row_wise=False, create_new=False)
    person_likes_message = merge_matrix(person_likes_comment, person_likes_post, row_wise=False, create_new=False)
    message_hastag_tag = merge_matrix(comment_hastag_tag, post_hastag_tag, row_wise=True, create_new=False)
    message_hascreator_person = merge_matrix(comment_hascreator_person, post_hascreator_person, row_wise=True, create_new=False)

    # these should not be used again, because these were overwritten during the merge...
    comment_replyof_comment = None
    person_likes_comment = None
    comment_hastag_tag = None
    comment_hascreator_person = None

    # print("Message matrices created\t%s" % logger.get_total_time(), file=stderr)

    # get index for given tag
    tag_index = tags.data.index([tag_name])

    # messages that have the given tag
    message_mask_vec = message_hastag_tag[:, tag_index].new()
    message_mask, _ = message_mask_vec.to_values()

    # calculate replies and likes for each message with the given tag
    def mult(r):
        def inner(val):
            return r * val
        return inner

    mult = UnaryOp.register_anonymous(mult, parameterized=True)

    # calculate points (and not count!) for each messages (due to replies)
    message_replies = comment_replyof_message \
        .reduce_columns().new(mask=StructuralMask(message_mask_vec)) \
        .apply(mult(points_per_reply)).new()

    # calculate points (and not count!) for each messages (due to likes)
    message_likes = person_likes_message \
        .reduce_columns().new(mask=StructuralMask(message_mask_vec)) \
        .apply(mult(points_per_like)).new()

    # covert message points to person points
    person_replies = message_replies.vxm(message_hascreator_person).new()
    person_likes = message_likes.vxm(message_hascreator_person).new()

    # calculate points for each person (due to messages)
    person_messages = message_hascreator_person[list(message_mask), :].new().reduce_columns().new()

    # calculate score per person
    person_points = person_replies.ewise_add(person_likes).new().ewise_add(person_messages).new().to_values()

    # print("Scores calculated\t%s" % logger.get_total_time(), file=stderr)

    # sort: score asc, person index desc
    sorted_result = sorted(zip(*person_points), key=lambda x: (-x[1], persons.index2id(x[0])))

    # print("Results sorted\t%s" % logger.get_total_time(), file=stderr)

    person_replies_dict = dict(zip(*person_replies.to_values()))
    person_likes_dict = dict(zip(*person_likes.to_values()))
    person_messages_dict = dict(zip(*person_messages.to_values()))

    logger.calculation_finished()

    for index, score in islice(sorted_result, result_limit):
        person_id = persons.index2id(index)
        reply_count = person_replies_dict.get(index, 0) // points_per_reply
        like_count = person_likes_dict.get(index, 0) // points_per_like
        message_count = person_messages_dict[index]
        print(f"{person_id};{reply_count};{like_count};{message_count};{score}")

    # print("All done\t%s" % logger.get_total_time(), file=stderr)
