import sqlite3
import urllib.parse

class MetaCounterHandler:
    def __init__(self, database: str) -> None:
        """
        Constructor of the ``MetaCounterHandler`` class.

        :param database: The name of the SQLite database file
        :type database: str
        """
        sqlite3.threadsafety = 3
        self.con = sqlite3.connect(database, check_same_thread=False)
        self.cur = self.con.cursor()

        self.base_iri = "https://w3id.org/oc/meta/"
        self.short_names = ["ar", "br", "id", "ra", "re"]
        self.supplier_prefix = "060"

        self.entity_type_abbr = {
            'http://purl.org/spar/fabio/Expression': 'br',
            'http://purl.org/spar/fabio/JournalArticle': 'br',
            'http://purl.org/spar/fabio/Book': 'br',
            'http://purl.org/spar/fabio/JournalIssue': 'br',
            'http://purl.org/spar/fabio/JournalVolume': 'br',
            'http://purl.org/spar/fabio/Journal': 'br',
            'http://purl.org/spar/pro/RoleInTime': 'ar',
            'http://purl.org/spar/fabio/Manifestation': 're',
            'http://xmlns.com/foaf/0.1/Agent': 'ra',
            'http://purl.org/spar/datacite/Identifier': 'id'
        }

        # Create table
        self.cur.execute("""CREATE TABLE IF NOT EXISTS counters(
            entity TEXT PRIMARY KEY, 
            count INTEGER)""")
        self.con.commit()

    def set_counter(self, new_value: int, entity_name: str) -> None:
        """
        It allows to set the counter value of provenance entities.

        :param new_value: The new counter value to be set
        :type new_value: int
        :param entity_name: The entity name
        :type entity_name: str
        :raises ValueError: if ``new_value`` is a negative integer.
        :return: None
        """
        if new_value < 0:
            raise ValueError("new_value must be a non negative integer!")
        
        if str(entity_name) in self.entity_type_abbr:
            entity_name = self.entity_type_abbr[str(entity_name)]
            self.cur.execute("INSERT OR REPLACE INTO counters (entity, count) VALUES (?, ?)", 
                            (entity_name, new_value))
            self.con.commit()

    def read_counter(self, entity_name: str) -> int:
        """
        It allows to read the counter value of provenance entities.

        :param entity_name: The entity name
        :type entity_name: str
        :return: The requested counter value.
        """
        if str(entity_name) in self.entity_type_abbr:
            entity_name = self.entity_type_abbr[str(entity_name)]
            self.cur.execute("SELECT count FROM counters WHERE entity=?", (entity_name,))
            result = self.cur.fetchone()
            
            if result:
                return result[0]
            else:
                return 0

    def increment_counter(self, entity_name: str) -> int:
        """
        It allows to increment the counter value of graph and provenance entities by one unit.

        :param entity_name: The entity name
        :type entity_name: str
        :return: The newly-updated (already incremented) counter value.
        """
        if str(entity_name) in self.entity_type_abbr:
            entity_name = self.entity_type_abbr[str(entity_name)]

            self.cur.execute("""INSERT INTO counters (entity, count) VALUES (?, 1)
                                ON CONFLICT(entity) DO UPDATE SET count = count + 1
                                RETURNING count""", (entity_name,))
            result = self.cur.fetchone()
            self.con.commit()
            
            return result[0]

    def close(self):
        """
        Closes the database connection.
        """
        if self.con:
            self.con.close()