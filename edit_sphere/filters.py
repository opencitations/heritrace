from __future__ import annotations

from typing import Tuple
from urllib.parse import urlparse, quote
from flask import url_for
from flask_babel import gettext
import dateutil
import validators
from flask_babel import format_datetime, lazy_gettext


class Filter:
    def __init__(self, context: dict, display_rules: dict):
        self.context = context
        self.display_rules = display_rules

    def human_readable_predicate(self, url: str, entity_classes: list, is_link: bool = True):
        subject_classes = [str(subject_class) for subject_class in entity_classes]
        if self.display_rules:
            for diplay_rule in self.display_rules:
                for subject_class in subject_classes:
                    if subject_class in diplay_rule['class']:
                        if url == subject_class:
                            return diplay_rule['displayName']
                        for display_property in diplay_rule['displayProperties']:
                            if display_property['property'] == str(url):
                                for value in display_property['values']:
                                    return value['displayName']
        first_part, last_part = self.split_ns(url)
        if first_part in self.context:
            if last_part.islower():
                return last_part
            else:
                words = []
                word = ""
                for char in last_part:
                    if char.isupper() and word:
                        words.append(word)
                        word = char
                    else:
                        word += char
                words.append(word)
                return " ".join(words).lower()
        elif validators.url(url) and is_link:
            return f"<a href='{url_for('show_triples', subject=quote(url))}' alt='{gettext('Link to the entity %(entity)s', entity=url)}'>{url}</a>"
        else:
            return url
    
    def human_readable_datetime(self, dt_str):
        dt = dateutil.parser.parse(dt_str)
        return format_datetime(dt, format='long')

    def split_ns(self, ns: str) -> Tuple[str, str]:
        parsed = urlparse(ns)
        if parsed.fragment:
            first_part = parsed.scheme + '://' + parsed.netloc + parsed.path + '#'
            last_part = parsed.fragment
        else:
            first_part = parsed.scheme + '://' + parsed.netloc + '/'.join(parsed.path.split('/')[:-1]) + '/'
            last_part = parsed.path.split('/')[-1]
        return first_part, last_part
    
    def human_readable_primary_source(self, primary_source: str|None) -> str:
        if primary_source is None:
            return lazy_gettext('Unknown')
        if '/prov/se' in primary_source:
            version_url = f"/entity-version/{primary_source.replace('/prov/se', '')}"
            return f"<a href='{version_url}' alt='{lazy_gettext('Link to the primary source description')}'>" + lazy_gettext('Version') + ' ' + primary_source.split('/prov/se/')[-1] + '</a>'
        else:
            if validators.url(primary_source):
                return f"<a href='{primary_source}' alt='{lazy_gettext('Link to the primary source description')} target='_blank'>{primary_source}</a>"
            else:
                return primary_source