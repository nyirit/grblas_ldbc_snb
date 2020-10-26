"""
LDBC SNB BI query 4. Top posters in a country
https://ldbc.github.io/ldbc_snb_docs_snapshot/bi-read-04.pdf

todo: results with 0 points are not added as of yet.
"""

from itertools import islice

from ldbc_snb_grblas.loader import Loader
from ldbc_snb_grblas.logger import Logger


def calc(data_dir, country_name):
    # init timer
    logger = Logger()

    # load vertices
    loader = Loader(data_dir)
    places = loader.load_vertex('place', column_names=['name', 'type'], is_dynamic=False)
    persons = loader.load_empty_vertex('person')
    forums = loader.load_empty_vertex('forum')
    posts = loader.load_empty_vertex('post')

    # print("Vertices loaded\t%s" % logger.get_total_time(), file=stderr)

    # get id of given country
    country_index = places.data.index([country_name, 'country'])

    # load edges
    place_ispartof_place = loader.load_edge(places, 'isPartOf', places, is_dynamic=False, rmask=(country_index,))
    cities_mask, _ = place_ispartof_place[:, country_index].new().to_values()

    person_islocatedin_place = loader.load_edge(persons, 'isLocatedIn', places, is_dynamic=True, rmask=cities_mask)
    members_mask, _ = person_islocatedin_place.reduce_rows().new().to_values()
    forum_hasmember_person = loader.load_edge(forums, 'hasMember', persons, is_dynamic=True, rmask=members_mask)

    # fixme: strictly not only loading was done until now, but some mask creations as well
    # print("Edges loaded\t%s" % logger.get_total_time(), file=stderr)

    logger.loading_finished()

    # calculate members per forum
    members_count_per_forum = forum_hasmember_person.reduce_rows().new()

    # calculate top 100 forums
    sorted_forums = sorted(zip(*members_count_per_forum.to_values()), key=lambda x: (-x[1], forums.index2id(x[0])))
    top_forums_mask = {index for index, _ in islice(sorted_forums, 100)}

    # print("Top forums calculated\t%s" % logger.get_total_time(), file=stderr)

    # calculate nr. of posts per person (not including people who don't have any posts)
    forum_containerof_post = loader.load_edge(forums, 'containerOf', posts, is_dynamic=True, lmask=top_forums_mask)
    posts_mask, _ = forum_containerof_post.reduce_columns().new().to_values()

    post_hascreator_person = loader.load_edge(posts, 'hasCreator', persons, is_dynamic=True, lmask=posts_mask)

    # create person->post_count dictionary
    persons_index, posts_count = post_hascreator_person.reduce_columns().new().to_values()[:2]
    result = zip(persons_index, posts_count)  # list of (person_index, post_count) 2-tuples
    sorted_results = sorted(result, key=lambda x: (-x[1], persons.index2id(x[0])))

    # if needed, get people who have 0 points as they have no posts
    if len(persons_index) < 100:
        # persons_set = set(persons_index)
        # TODO add people with 0 points...
        pass

    # load person attributes
    persons_data = loader.load_vertex('person', column_names=['firstName', 'lastName', 'creationDate'],
                                      is_dynamic=True)
    persons_dict = persons_data.get_index_data_dict()

    logger.calculation_finished()

    for person_index, posts_count in islice(sorted_results, 100):
        person_id = persons.index2id(person_index)
        first_name, last_name, creation_date = persons_dict[person_index]
        print(f"{person_id};{first_name};{last_name};{creation_date};{posts_count}")

    # print("All done\t%s" % logger.get_total_time(), file=stderr)
