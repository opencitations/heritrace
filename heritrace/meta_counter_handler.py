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
            'http://purl.org/spar/fabio/BookChapter': 'br',
            'http://purl.org/spar/fabio/JournalIssue': 'br',
            'http://purl.org/spar/fabio/JournalVolume': 'br',
            'http://purl.org/spar/fabio/Journal': 'br',
            'http://purl.org/spar/fabio/AcademicProceedings': 'br',
            'http://purl.org/spar/fabio/ProceedingsPaper': 'br',
            'http://purl.org/spar/fabio/ReferenceBook': 'br',
            'http://purl.org/spar/fabio/Review': 'br',
            'http://purl.org/spar/fabio/ReviewArticle': 'br',
            'http://purl.org/spar/fabio/Series': 'br',
            'http://purl.org/spar/fabio/Thesis': 'br',
            'http://purl.org/spar/pro/RoleInTime': 'ar',
            'http://purl.org/spar/fabio/Manifestation': 're',
            'http://xmlns.com/foaf/0.1/Agent': 'ra',
            'http://purl.org/spar/datacite/Identifier': 'id'
        }

        # Create tables
        self.cur.execute("""CREATE TABLE IF NOT EXISTS data_counters(
            entity TEXT PRIMARY KEY, 
            count INTEGER)""")
        self.cur.execute("""CREATE TABLE IF NOT EXISTS prov_counters(
            entity TEXT PRIMARY KEY, 
            count INTEGER)""")
        self.con.commit()

    def _process_entity_name(self, entity_name: str) -> tuple:
        """
        Process the entity name, determine the table to use, and format the entity name.

        :param entity_name: The entity name
        :type entity_name: str
        :return: A tuple containing the table name and the processed entity name
        :rtype: tuple
        """
        entity_name_str = str(entity_name)
        if entity_name_str in self.entity_type_abbr:
            return ('data_counters', self.entity_type_abbr[entity_name_str])
        else:
            return ('prov_counters', urllib.parse.quote(entity_name_str))

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
        
        table, processed_entity_name = self._process_entity_name(entity_name)
        self.cur.execute(f"INSERT OR REPLACE INTO {table} (entity, count) VALUES (?, ?)", 
                        (processed_entity_name, new_value))
        self.con.commit()

    def read_counter(self, entity_name: str) -> int:
        """
        It allows to read the counter value of provenance entities.

        :param entity_name: The entity name
        :type entity_name: str
        :return: The requested counter value.
        """
        table, processed_entity_name = self._process_entity_name(entity_name)
        self.cur.execute(f"SELECT count FROM {table} WHERE entity=?", (processed_entity_name,))
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
        current_count = self.read_counter(entity_name)
        new_count = current_count + 1
        self.set_counter(new_count, entity_name)
        return new_count

    def close(self):
        """
        Closes the database connection.
        """
        if self.con:
            self.con.close()