from dbutils.enhanced_jdbc_provider import QueryWorker


class FakeCursor:
    def __init__(self):
        self.description = (('col1',),)
        self.rows = [(1,), (2,), (3,)]

    def execute(self, sql):
        pass

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class FakeConn:
    def cursor(self):
        return FakeCursor()


def test_queryworker_cancel_before_run():
    w = QueryWorker(FakeConn(), 'SELECT 1')
    # cancel before run should just finish
    w.cancel()
    # Running should not raise
    w.run()


def test_queryworker_handles_cursor_exceptions(monkeypatch):
    def bad_cursor():
        class Bc:
            description = None

            def execute(self, sql):
                raise RuntimeError('fail')

            def close(self):
                pass

        return Bc()

    class FakeConn2:
        def cursor(self):
            return bad_cursor()

    w = QueryWorker(FakeConn2(), 'SELECT 1')
    # Should not raise when run is called
    w.run()

