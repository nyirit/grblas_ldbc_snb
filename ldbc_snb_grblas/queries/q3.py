"""
LDBC SNB BI query 3. Popular topics in a country
https://ldbc.github.io/ldbc_snb_docs_snapshot/bi-read-03.pdf
"""

from itertools import islice

from sys import stderr

from time import perf_counter

from ldbc_snb_grblas.loader import Loader


def calc(data_dir, tag_class_name, country_name):
    # init timer
    time_start = perf_counter()

    # load data sets
    loader = Loader(data_dir)

    forums = loader.load_vertex_type('forum', column_names=['title', 'creationDate'], is_dynamic=True)
    tag_class = loader.load_vertex_type('tagclass', column_names=['name'], is_dynamic=False)
    places = loader.load_vertex_type('place', column_names=['name', 'type'], is_dynamic=False)

    tags = loader.load_empty_vertex('tag')
    persons = loader.load_empty_vertex('person')
    posts = loader.load_empty_vertex('post')

    print("Vertices loaded\t%s" % (perf_counter() - time_start), file=stderr)

    # get id of given tag class
    tag_class_index = tag_class.data.index([tag_class_name])

    # load tags belonging to given tag class
    tag_hastype_tagclass = loader.load_edge_type(tags, 'hasType', tag_class, is_dynamic=False,
                                                 rmask=[tag_class_index])

    # get id of given country
    country_id = places.data.index([country_name, 'country'])

    # get cities that are directly part of the given country
    place_ispartof_place = loader.load_edge_type(places, 'isPartOf', places, is_dynamic=False)
    cities_mask, _ = place_ispartof_place[:, country_id].new().to_values()

    # get persons located in given cities
    person_islocatedin_city = loader.load_edge_type(persons, 'isLocatedIn', places, is_dynamic=True,
                                                    rmask=cities_mask)

    persons_mask, _ = person_islocatedin_city.reduce_rows().new().to_values()
    forum_hasmoderator_person = loader.load_edge_type(forums, 'hasModerator', persons, is_dynamic=True,
                                                      rmask=persons_mask)

    moderators = dict(zip(*forum_hasmoderator_person.to_values()[:2]))

    # tags that are directly connected to the tag_class parameter
    tags_mask, _ = tag_hastype_tagclass[:, tag_class_index].new().to_values()

    # get posts with tags
    post_hastag_tag = loader.load_edge_type(posts, 'hasTag', tags, is_dynamic=True,
                                            rmask=tags_mask)
    posts_mask, _ = post_hastag_tag.reduce_rows().new().to_values()

    # forums that are located in the given country
    forums_mask, _ = forum_hasmoderator_person.reduce_rows().new().to_values()

    # get posts for forums that are connected to the given tag
    forum_containerof_post = loader.load_edge_type(forums, 'containerOf', posts, is_dynamic=True,
                                                   lmask=forums_mask, rmask=posts_mask)

    # reduce to gte post count
    posts_per_forum = forum_containerof_post.reduce_rows().new()

    print("Results calculated\t%s" % (perf_counter() - time_start), file=stderr)

    # sort results
    result = sorted(zip(*posts_per_forum.to_values()), key=lambda x: (-x[1], x[0]))
    print("Data sorted\t%s" % (perf_counter() - time_start), file=stderr)

    # print results
    for forum_index, post_count in islice(result, 20):
        forum_id = forums.index2id(forum_index)
        forum_title = forums.data[forum_index][0]
        forum_date = forums.data[forum_index][1]
        person_id = persons.index2id(moderators[forum_index])
        print(f"{forum_id};{forum_title};{forum_date};{person_id};{post_count}")

    print("All done\t%s" % (perf_counter() - time_start), file=stderr)
