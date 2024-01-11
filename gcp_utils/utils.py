"""Utility Functions"""
# Standard imports
import ast
from datetime import datetime
import hashlib
import json
import os
import re
import string
import tempfile
import time
import urllib3
import uuid
from functools import wraps
from time import time


# Third-party imports
import dateutil.parser
import dirtyjson
import pytz

try:
    import proto
    DATETIME_CLS = proto.datetime_helpers.DatetimeWithNanoseconds
except ModuleNotFoundError:
    DATETIME_CLS = datetime

DICT_CAT_OVERWRITES = {"id", "role", "user", "object", "model", "finish_reason"}

DUCK_INT_MAP = {
    "": None,
    "true": 1,
    "false": 0,
    "null": None,
    "none": None,
    "nan": None,
}

RE_ISO_DATETIME = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})?$')

RE_PARSE_CODE_JSON = re.compile(r'^\{\s*"([a-z]+_code)":\s*"(.*?)("\s*\})?$',
                                re.DOTALL)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        from settings import LazySetting
        if hasattr(obj, "isoformat"):  # datetime or DatetimeWithNanoseconds
            return obj.isoformat()
        elif isinstance(obj, LazySetting):
            return obj.get()
        return super(CustomJSONEncoder, self).default(obj)


class CustomJSONDecoder(json.JSONDecoder):
    def object_hook(self, dct):
        from settings import LazySetting

        for key, value in dct.items():
            if isinstance(value, LazySetting):
                dct[key] = str(value)
            elif isinstance(value, str) and RE_ISO_DATETIME.match(value):
                try:
                    dct[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass
        return dct


def base36(num):
    """Generate a base 36 string representation of an integer"""
    assert isinstance(num, int), "base36() requires an integer (<%s> %s)" % (
        type(num), num)
    alphabet = '0123456789abcdefghijklmnopqrstuvwxyz'
    base36 = ''
    while num:
        num, i = divmod(num, 36)
        base36 = alphabet[i] + base36
    return base36


def clean_temp_dir(directory=None, max_age=300):
    """Remove old files from a directory recursively"""
    from settings import logger

    directory = directory or tempfile.gettempdir()
    now = time.time()
    count = 0

    try:
        listing = os.listdir(directory)
    except (OSError, PermissionError):
        return 0

    for filename in listing:
        file_path = os.path.join(directory, filename)

        try:
            file_modified = os.path.getmtime(file_path)
            file_age = now - file_modified
        except (OSError, PermissionError):
            continue

        if os.path.isfile(file_path):
            try:
                if file_age > max_age:
                    logger.debug("[clean_temp_dir] FILE: %s", file_path)
                    os.remove(file_path)
                    count += 1
            except (OSError, PermissionError) as exc:
                logger.debug("[clean_temp_dir] ERR: %s (%s)", file_path, exc)
        elif os.path.isdir(file_path):
            subdir_count = clean_temp_dir(file_path, max_age)
            count += subdir_count
            try:
                # only remove directory if files were removed and it's stale
                if subdir_count > 0 and file_age > max_age:
                    logger.debug("[clean_temp_dir] DIR: %s", file_path)
                    os.removedirs(file_path)
            except (OSError, PermissionError) as exc:
                logger.debug("[clean_temp_dir] ERR: %s (%s)", file_path, exc)

    return count


def df_schema(filename_or_df, hints=None, sample_k=10, len_k=25):
    """Use Pandas to generate a schema from a dataframe"""
    # Third-party imports
    import pandas as pd

    def get_possible_values(df, column_name):
        column = df[column_name]
        possible_values = {}

        for value in column:
            key = value
            try:
                n = float(value)
                if n.is_integer():
                    i = int(n)
                    if i in {-1, 0, 1}:
                        key = str(i)
                    else:
                        key = "int64"
                else:
                    key = "float64"
            except ValueError:
                key = value[:len_k-3] + '...' if len(value) > len_k else value
            possible_values[key] = possible_values.get(key, 0) + 1

        # create dict with keys sorted by highest value first
        possible_values = dict(sorted(
            possible_values.items(), key=lambda item: item[1], reverse=True))

        return possible_values

    if isinstance(filename_or_df, str):
        df = pd.read_csv(filename_or_df)
    else:
        df = filename_or_df
    column_schemas = []

    coercions_nan = set()
    coercions_nat = set()
    exclusions_nan = set()

    for column_name, dtype in df.dtypes.items():
        column_schema = {
            'name': column_name,
            'dtype': str(dtype),
        }
        if dtype == "object":
            possible_values = get_possible_values(df, column_name)
            if subscript(possible_values.keys(), 0) == "float64":
                coercions_nan.add(column_name)
            dtypes = set()
            samples = []
            for value, count in possible_values.items():
                if value in {'int64', 'float64'}:
                    dtypes.add(value)
                # elif value in {'1', '0', '-1'}:
                #     exclusions_nan.add(value)  # ignore these if mostly float64
                #     samples.append(value)
                else:
                    dtypes.add('string')
                    samples.append(value)
            column_schema['dtype'] = ','.join(dtypes)

            # use mostly samples from the highest frequency but some lowest too
            if len(samples) > sample_k:
                mostly_k = int(sample_k * 0.75)
                also_k = sample_k - mostly_k
                samples = samples[:mostly_k] + samples[-also_k:]

            column_schema['samples'] = '\n'.join(samples)

        elif dtype == "string":
            possible_values = get_possible_values(df, column_name)
            column_schema['samples'] = '\n'.join(list(
                possible_values.keys())[:sample_k])

        if re.search(r'(date|time|_at|created|updated)', column_name, re.I):
            coercions_nat.add(column_name)

        column_schemas.append(column_schema)

    if hints is not None:
        if coercions_nan:    
            hint = "".join(["ALWAYS coerce non-numeric values in `",
                            "`, `".join(sorted(coercions_nan)), "` to NaN"])
            if exclusions_nan:
                hint += " and ignore " + ", ".join(sorted(exclusions_nan))
            hints.append(hint)

        if coercions_nat:
            hints.append("ALWAYS coerce non-datetime values in `"
                         + "`, `".join(sorted(coercions_nat))
                         + "` to NaT (Not a Time)")

    return column_schemas


def dict_cat(basedict, fragdict, overwrites=DICT_CAT_OVERWRITES):
    """Update a base dictionary with a fragment; concatenate any values found"""
    for key, value in fragdict.items():
        if key in basedict:
            if key in overwrites:
                basedict[key] = value
            elif isinstance(basedict[key], str) and isinstance(value, str):
                basedict[key] = basedict[key] + value
            elif isinstance(basedict[key], dict) and isinstance(value, dict):
                dict_cat(basedict[key], value)
            elif isinstance(basedict[key], list) and isinstance(value, list):
                baselist = basedict[key]
                fraglist = value
                for i in range(len(fraglist)):
                    if i < len(baselist):
                        if isinstance(baselist[i], str) and isinstance(fraglist[i], str):
                            baselist[i] = baselist[i] + fraglist[i]
                        elif isinstance(baselist[i], dict) and isinstance(fraglist[i], dict):
                            dict_cat(baselist[i], fraglist[i])
                        else:
                            baselist[i] = fraglist[i]
                    else:
                        baselist.append(fraglist[i])
            else:
                basedict[key] = value
        else:
            basedict[key] = value

    return basedict


def dict_extract(basedict, endswith=None, readonly=False):
    """Remove keys based on filters and return them in a new dict
    :param basedict: The dictionary to extract from.
    :param endswith: String to match the end of a key name.
    :param readonly: If True, do not remove keys from the basedict.
    """
    extractdict = {}
    for keys in list(basedict.keys()):
        matched = False
        if endswith is not None and keys.endswith(endswith):
            matched = True

        if matched:
            extractdict[keys] = basedict[keys]
            if not readonly:
                del basedict[keys]

    return extractdict


def dict_prune(basedict, keep_keys):
    """Remove any keys from a dictionary that are not in the keep_keys list"""
    assert isinstance(basedict, dict), "dict_prune() requires a dict"
    for key in list(basedict.keys()):
        if key not in keep_keys:
            del basedict[key]
        elif isinstance(basedict[key], dict):
            dict_prune(basedict[key], keep_keys)
    return basedict


def duck_bool(value, default=False):
    """Duck-typed boolean value
    :param value: Value to interpret as bool
    :param default: Default value if value is None"""
    if value is None:
        assert default in {True, False}, "Default must be True or False"
        return default
    elif isinstance(value, (bool, float, int)):
        return bool(value)

    true_values = ["true", "1", "yes"]
    false_values = ["false", "0", "no"]

    value_lower = value.lower()

    if value_lower in true_values:
        return True
    elif value_lower in false_values:
        return False
    else:
        raise ValueError(f"Cannot convert '{value}' ({type(value)}) to bool")


def duck_bytes(value):
    """Duck-typed bytes value
    :param value: Value to interpret as bytes"""
    if isinstance(value, bytes):
        return value
    elif value is None:
        return b''
    elif isinstance(value, dict):
        circular_key = find_circular_ref(value)
        assert circular_key is None, "Circular reference in dict: %s" % (
            circular_key)
        return json.dumps(value, cls=CustomJSONEncoder).encode('utf-8')
    elif isinstance(value, str):
        return value.encode('utf-8')
    elif isinstance(value, (int, float)):
        return str(value).encode('utf-8')
    else:
        raise ValueError(f"Cannot convert '{value}' ({type(value)}) to bytes")


def duck_datetime(value):
    """Duck-typed datetime value must be offset-aware"""
    from settings import LazySetting
    if isinstance(value, LazySetting):
        value = str(value)
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            # No timezone specified, default to UTC
            value = value.replace(tzinfo=pytz.UTC)
        return value

    dt = dateutil.parser.isoparse(value)
    if dt.tzinfo is None:
        # No timezone specified, default to UTC
        dt = dt.replace(tzinfo=pytz.UTC)

    return dt


def duck_dict(value, strict=False):
    """Duck-typed dict value
    (performs JSON decoding; use in place of `json.loads`)"""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value, cls=CustomJSONDecoder)
        except json.JSONDecodeError as exc:
            if strict:
                raise

            from settings import logger
            logger.debug("INVALID JSON (%s): <JSON>%s</JSON>", exc, value)

            try:
                d = dirtyjson.loads(value)
                if d is not None:  # convert to dict from dirtyjson object
                    return dict(d)
            except Exception as exc:
                if not value.startswith("{"):
                    raise

                try:
                    return ast.literal_eval(value)  # try Python-formatted data
                except SyntaxError:
                    m = RE_PARSE_CODE_JSON.match(value)
                    if not m:
                        raise
                    return {m.group(1): m.group(2)}

    return dict(value)


def duck_int(value, default=None, strict=False):
    """Duck-typed int value"""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip().lower()
        if value in DUCK_INT_MAP:
            return duck_int(DUCK_INT_MAP[value], default=default)

    try:
        return int(value)
    except ValueError:
        if strict:
            raise
        return default


def duck_list(value, default=None, enum=None):
    """Duck-typed list value"""
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        l = list(value)
    elif isinstance(value, str) and value.startswith("["):
        l = json.loads(value, cls=CustomJSONDecoder)
    elif isinstance(value, str) and value == "":
        return []
    else:
        l = value.split(",")

    # assert if any items do not match enum collection
    if enum is not None:
        for item in l:
            if item not in enum:
                raise ValueError(
                    f"Invalid item in list: {item} (expected={enum})")
    return l


def duck_str(value, default=None, pretty=False):
    """Duck-typed string value
    (performs JSON encoding; use in place of `json.dumps`)"""
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list, tuple)):
        kwargs = {
            'indent': 2,
            'sort_keys': True
        } if pretty else {}
        return json.dumps(value, cls=CustomJSONEncoder, **kwargs)
    return str(value)


def duck_var(value, name=None):
    """Attempt to convert an arbitrary string to a typed value"""
    if not isinstance(value, str):
        return value

    if name is not None:
        if name.endswith("_ids"):
            return duck_list(value)
        elif name.endswith("_k"):
            if value == "null" or value == "None":
                return None
            return int(value)
        elif name == "text":
            return value

    if value.startswith("{") and value.endswith("}"):
        return duck_dict(value)

    elif value.startswith("[") and value.endswith("]"):
        return duck_list(value)

    return value


def find_circular_ref(obj, seen=None, path=[]):
    """Find circular references in a data structure"""
    if not isinstance(obj, (dict, list, tuple, set)):  # ignore "primitives"
        return None

    obj_id = id(obj)

    if seen is None:
        seen = {}

    if obj_id in seen:
        return path

    seen[obj_id] = True

    if isinstance(obj, dict):
        for key, value in obj.items():
            circular_path = find_circular_ref(value, seen, path + [str(key)])
            if circular_path:
                return circular_path
    elif isinstance(obj, (list, tuple, set)):
        for index, item in enumerate(obj):
            circular_path = find_circular_ref(item, seen, path + [str(index)])
            if circular_path:
                return circular_path

    return None


def first(collection):
    """Return the first item in a collection"""
    return next(iter(collection))


def generate_words(s, delay=0.05):
    """Generate words from a string"""
    for word in re.findall(r'\S+|\s+', s):
        yield word
        if delay > 0:
            time.sleep(delay)


def get_figure_title(fig):
    """Get best title of a matplotlib Figure"""
    suptitle = fig._suptitle  # Check for suptitle aka super title
    if suptitle:
        return suptitle.get_text()

    for ax in fig.get_axes():  # Check for title on each axis
        title = ax.get_title()
        if title:
            return title

    for child in fig.get_children():  # Check for text on each text element
        if hasattr(child, 'get_text'):
            text = child.get_text()
            if text:
                return text

    # If no title found, return empty string
    return ''


def hash_file(filename):
    """Generates SHA-256 hash of the file passed into it"""
    h = hashlib.sha256()

    # open file for reading in binary mode
    with open(filename, 'rb') as file:
        # loop till the end of the file
        chunk = 0
        while chunk != b'':
            # read only 1024 bytes at a time
            chunk = file.read(1024)
            h.update(chunk)

    # return the hex representation of digest
    return h.hexdigest()


def idhash(**kwargs):
    """Sort and hash fields with names ending in `_id` to create a unique ID"""
    id_fields = [key for key in kwargs.keys() if key.endswith('_id')]
    assert id_fields, "No ID Fields: %s" % (kwargs,)
    id_fields.sort()
    str_to_hash = '\0'.join([str(kwargs[key]) for key in id_fields])
    bytes_to_hash = str_to_hash.encode('utf-8')
    id = hashlib.sha256(bytes_to_hash).hexdigest()
    return id


def is_content_url(value, schemes={"http", "https"}):
    """Return True if the value is a URL for content else False"""
    if value is None or not isinstance(value, str):
        return False

    # fail if value contains any whitespace characters
    if any(c in value for c in string.whitespace):
        return False

    # value must start with a scheme
    if ":" not in value:
        return False
    scheme = value.split(":", 1)[0]
    if scheme not in schemes:
        return False

    # use urllib3 to validate URL
    try:
        u = urllib3.util.parse_url(value)
    except:
        return False

    # must have path
    if not u.path or u.path == '/':
        return False

    return True


def is_list(value):
    """Return True if the value is a list or tuple else False"""
    return isinstance(value, (list, tuple))


def is_list_of_primitives(value):
    """Return True if the value is a list of objects else False"""
    if not is_list(value):
        return False
    return all(is_primitive(v) for v in value)


def is_primitive(value):
    """Return True if the value is a primitive type else False"""
    # NOTE: datetime is included because it can be perfectly serialized by str()
    # and the point is whether or not the value needs special processing or not
    return isinstance(value, (bool, datetime, float, int, str))


def is_vector(value):
    """Return True if the value is a list of floats"""
    if not is_list(value):
        return False
    return all(isinstance(v, float) for v in value)


def last_line(value, default=None):
    """Return the last line of a string"""
    lines = value.splitlines()
    i = len(lines) - 1
    while i >= 0:
        line = lines[i].strip()
        if line:
            return line
        i -= 1
    return default


def sanitize(map, maxdepth=5, exclude=None, _depth=0):
    """Recursively remove private attributes from a dict"""
    exclude = {} if exclude is None else exclude
    if _depth > maxdepth:
        return map

    if isinstance(map, dict):
        return {k: sanitize(v, maxdepth, exclude, _depth + 1)
                for k, v in map.items() if not k.startswith('_')}

    if isinstance(map, (list, tuple)):
        return [sanitize(v, maxdepth, exclude, _depth + 1) for v in map]

    return map



def some_text(value, limit=100):
    """Return a flat string representation of a value
    :param value: The value to convert to a string.
    :param limit: The maximum length of the string."""
    if isinstance(value, str):
        s = value[:limit]
    elif isinstance(value, (list, tuple)):
        s = " ".join([some_text(v) for v in value])
    elif isinstance(value, dict):
        s = " ".join([some_text(v) for v in value.values()])
    else:
        s = str(value)

    # flatten string to remove newlines and extra whitespace
    s = " ".join(s.split())

    # truncate if too long and fit in ellipses suffix ...
    if len(s) > limit:
        s = s[:limit - 3] + "..."

    return s


def subscript(value, index, default=None, strict=False):
    """Return subscript by index of a list or dict"""
    if value is None:
        if strict:
            raise TypeError("Cannot subscript None")
        return default

    # annoying HACK because .keys() doesn't return a tuple/list
    if isinstance(value, type({}.keys())):
        return subscript(list(value), index, default=default, strict=strict)

    if isinstance(value, dict):
        return value.get(index, default)

    elif is_list(value):
        try:
            return value[index]
        except IndexError:
            if strict:
                raise
            return default

    if strict:
        raise TypeError("Cannot subscript <%s> %s" % (type(value), value))
    return default


def tznow():
    """Return the current time in UTC"""
    return DATETIME_CLS.utcnow().replace(tzinfo=pytz.UTC)


def uuidgen():
    """Generate a UUID"""
    return str(uuid.uuid4())


def timing(f):
    from .settings import logger

    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        logger.debug('func:%r args:[%r, %r] took: %2.4f sec' % \
          (f.__name__, args, kw, te-ts))
        return result
    return wrap
