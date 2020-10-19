"""
LDBC SNB BI query 7. Related topics
https://ldbc.github.io/ldbc_snb_docs_snapshot/bi-read-07.pdf
"""
from itertools import islice

from grblas.mask import StructuralMask

from ldbc_snb_grblas.loader import Loader
from ldbc_snb_grblas.logger import Logger

result_limit = 100


def calc(data_dir, tag_name):
    # init timer
    logger = Logger()

    # load vertices
    loader = Loader(data_dir)
    tags = loader.load_vertex('tag', column_names=['name'], is_dynamic=False)
    posts = loader.load_empty_vertex('post')
    comments = loader.load_empty_vertex('comment')

    # print("Vertices loaded\t%s" % logger.get_total_time(), file=stderr)

    comment_hastag_tag = loader.load_edge(comments, 'hasTag', tags, is_dynamic=True)
    post_hastag_tag = loader.load_edge(posts, 'hasTag', tags, is_dynamic=True)
    comment_replyof_post = loader.load_edge(comments, 'replyOf', posts, is_dynamic=True, to_id_header_override='ParentPost.id')
    comment_replyof_comment = loader.load_edge(comments, 'replyOf', comments, is_dynamic=True, to_id_header_override='ParentComment.id')

    # print("Edges loaded\t%s" % logger.get_total_time(), file=stderr)

    logger.loading_finished()

    # get comments and posts with given tag
    tag_index = tags.data.index([tag_name])
    comments_with_tag = comment_hastag_tag[:, tag_index].new()
    posts_with_tag = post_hastag_tag[:, tag_index].new()

    # the length of post_hastag_tag is not equal to the number of all posts, but to the number of posts with given tag
    # and the same for comments
    posts_with_tag.resize(posts.length)
    comments_with_tag.resize(comments.length)

    # get comments that are replies of a post and comments that are replies of another comment
    post_replies = comment_replyof_post.mxv(posts_with_tag).new()
    comment_replies = comment_replyof_comment.mxv(comments_with_tag).new()

    # after getting post and comment replies, make sure their size match
    post_replies.resize(comments.length)
    comment_replies.resize(comments.length)

    # merge post and comment replies, but only those that do not have the given tag
    # (note: at this point there are messages that do not have any tags. These will be filtered out later)
    message_replies = post_replies.ewise_add(comment_replies).new(mask=~StructuralMask(comments_with_tag))

    # get tags for reply comments
    message_replies.resize(comment_hastag_tag.nrows)
    reply_tags_count = message_replies.vxm(comment_hastag_tag).new().to_values()

    # print("Counts calculated\t%s" % logger.get_total_time(), file=stderr)

    # todo: adding the name only for the top 100 could be useful, but the name is used for sorting
    # todo: so additional logic would be needed

    # map (tag_index, count) -> (tag_name, count)
    result = map(lambda x: (tags.data[x[0]][0], x[1]), zip(*reply_tags_count))
    # print("Tag name added\t%s" % logger.get_total_time(), file=stderr)

    sorted_result = sorted(result, key=lambda x: (-x[1], x[0]))  # order: count asc, name desc
    # print("Results sorted\t%s" % logger.get_total_time(), file=stderr)

    logger.calculation_finished()

    # print results...
    for name, count in islice(sorted_result, result_limit):
        print(f"{name};{count}")

    # print("All done\t%s" % logger.get_total_time(), file=stderr)
    logger.print_finished()
