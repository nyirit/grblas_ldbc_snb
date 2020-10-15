import pytz
from dateutil.parser import isoparse


def parse_user_date(date_str):
    date = isoparse(date_str)

    # add timezone if not present already
    if date.tzinfo is None:
        date = pytz.utc.localize(date)

    return date


def get_date_mask(vertex_type, data_index, start_date, end_date):
    """
    Creates a set containing the index of elements that has a creation date between start_date and end_date
    :param vertex_type:
    :param start_date:
    :param end_date:
    :return:
    """
    mask_indexes = set()
    for i, data in enumerate(vertex_type.data):
        creation_date_str = data[data_index]
        creation_date = isoparse(creation_date_str)
        if start_date <= creation_date <= end_date:
            mask_indexes.add(i)

    return mask_indexes
