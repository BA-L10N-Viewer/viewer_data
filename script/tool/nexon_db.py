class NexonDatabase:
    def __init__(self, db: list, key: str = "Id"):
        self.db = db
        self.key = key

    def query(self, keyword, default=None, raise_exception=False):
        if default is None:
            default = {}

        try:
            return self.db[self.query_pos(keyword)]
        except Exception as e:
            if raise_exception:
                raise e
            return default

    def query_pos(self, keyword):
        for (pos, i) in enumerate(self.db):
            if keyword == i[self.key]:
                return pos
        return float("-inf")
