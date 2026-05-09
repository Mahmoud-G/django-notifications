''' Django notifications utils file '''
# -*- coding: utf-8 -*-


def id2slug(id_value):
    """Encode a notification PK as a URL-safe numeric slug."""
    return str(int(id_value) + 110909)


def slug2id(slug):
    """Decode a numeric slug back to a notification PK."""
    return int(slug) - 110909
