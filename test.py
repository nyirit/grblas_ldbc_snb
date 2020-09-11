# import numpy as np
# import pandas as pd
# import networkx as nx
# import matplotlib.pyplot as plt
# import grblas as gb
# from grblas import Matrix, Vector, Scalar
# from grblas.base import NULL
# from grblas import dtypes
# from grblas import descriptor
# from grblas import unary, binary, monoid, semiring
# from grblas import io as gio

from grblas import Matrix, Vector
from grblas import dtypes

# ############# dummy data ################
post_hascreator_person = [
    # post id, creator id
    (0, 0),
    (1, 0),
    (2, 2),
]
comment_replyof_post = [
    # comment id, post id
    (0, 0),
    (1, 0),
    (3, 2),
    (5, 0),
]
comment_replyof_comment = [
    # child comment id, parent comment id
    (2, 0),
    (4, 2),
]

# ############# dummy code ################
num_of_comments = 6
num_of_posts = 3
num_of_persons = 3

a, b = zip(*post_hascreator_person)
M_post_person = Matrix.from_values(a, b, len(a)*[1], nrows=num_of_posts, ncols=num_of_persons, dtype=dtypes.INT32, name="post_hascreator_person")
a, b = zip(*comment_replyof_post)
M_comment_post = Matrix.from_values(a, b, len(a)*[1], nrows=num_of_comments, ncols=num_of_posts, dtype=dtypes.INT32, name="comment_replyof_post")
a, b = zip(*comment_replyof_comment)
M_comment_comment = Matrix.from_values(a, b, len(a)*[1], nrows=num_of_comments, ncols=num_of_comments, dtype=dtypes.INT32, name="comment_replyof_comment")

# todo filter messages by dates

# create matrix for the final results
MResult = Matrix.new(dtypes.INT32, nrows=num_of_persons, ncols=2, name='Result')

# get number of posts (initiated threads) per persons
V_count = Vector.new(dtypes.INT32, M_post_person.ncols, name="Vcount")
V_count << M_post_person.reduce_columns()

MResult[:, 0] << V_count

print("!! threads", MResult)

# get direct replies for each post as a person-comment matrix
Mw = Matrix.new(dtypes.INT32, nrows=num_of_persons, ncols=num_of_comments, name="Mw")
Mw << M_post_person.T.mxm(M_comment_post.T)

# calculate number of direct comments for persons
V_count << V_count.ewise_add(Mw.reduce_rows().new())

# get all comments iteratively per person
d = 0
while Mw.nvals > 0:
    # get next comments
    Mw << Mw.mxm(M_comment_comment.T)

    # add the vectors as rows to Mt matrix
    V_count << V_count.ewise_add(Mw.reduce_rows().new())

    d += 1

print("all comments ", V_count)

MResult[:, 1] << V_count

print(MResult)