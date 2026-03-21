# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, name, orcid):
        self.id = id
        self.name = name
        self.orcid = orcid
