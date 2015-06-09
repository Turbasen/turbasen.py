import turbasen

def test_configure():
    turbasen.configure(
        LIMIT=30,
    )
    assert turbasen.settings.Settings.LIMIT == 30
