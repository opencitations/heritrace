# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace

from flask import g

Params = tuple[tuple[str, str | int], ...]


# A rule that a save breaks, named by a code that the client turns into a
# message in the language of the interface. The subject and the predicate say
# which field the client shows it beside: the subject is the IRI of a resource,
# or the temporary id of one that the save creates.
@dataclass(frozen=True)
class FieldError:
    code: str
    subject: str | None = None
    predicate: str | None = None
    params: Params = ()

    def as_json(self) -> dict[str, object]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "code": self.code,
            "params": dict(self.params),
        }


def field_error(
    code: str,
    subject: str | None = None,
    predicate: str | None = None,
    **params: str | int,
) -> FieldError:
    return FieldError(
        code,
        None if subject is None else str(subject),
        None if predicate is None else str(predicate),
        tuple(sorted(params.items())),
    )


class RejectedError(Exception):
    def __init__(self, errors: Iterable[FieldError]) -> None:
        self.errors = list(dict.fromkeys(errors))
        super().__init__(
            "; ".join(
                f"{error.subject} {error.predicate}: {error.code} {dict(error.params)}"
                for error in self.errors
            )
        )

    def with_subjects(self, rename: Callable[[str], str | None]) -> "RejectedError":
        return RejectedError(
            replace(error, subject=rename(error.subject))
            if error.subject is not None
            else error
            for error in self.errors
        )


# The resources that a save creates have no IRI on the client, which names
# them by a temporary id, or names the resource that a creation request makes
# by no id at all. The rejection of the save uses the same names.
def name_new_resource(uri: str, temporary_id: str | None) -> None:
    g.setdefault("temporary_ids", {})[uri] = temporary_id


def client_names(error: RejectedError) -> RejectedError:
    names: dict[str, str | None] = g.setdefault("temporary_ids", {})
    return error.with_subjects(lambda subject: names.get(subject, subject))
