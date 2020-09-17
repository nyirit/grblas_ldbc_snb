import pytz
from dateutil.parser import isoparse


def parse_user_date(date_str):
    date = isoparse(date_str)

    # add timezone if not present already
    if date.tzinfo is None:
        date = pytz.utc.localize(date)

    return date
