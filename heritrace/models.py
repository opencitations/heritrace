from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, name, orcid):
        self.id = id
        self.name = name
        self.orcid = orcid
