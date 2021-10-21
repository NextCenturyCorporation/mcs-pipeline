import time


def get_date_in_file_format():
    """Get the date in a format like 2020-03-01, useful for creating files"""
    return time.strftime('%Y-%m-%d', time.localtime(time.time()))
