from canvas_dl.utils import parse_link_header


def test_parse_link_header():
    link = '<https://api.example.com/courses?page=2>; rel="next", <https://api.example.com/courses?page=10>; rel="last"'
    links = parse_link_header(link)
    assert links["next"].endswith("page=2")
    assert links["last"].endswith("page=10")


def test_parse_link_header_empty():
    assert parse_link_header(None) == {}
    assert parse_link_header("") == {}
