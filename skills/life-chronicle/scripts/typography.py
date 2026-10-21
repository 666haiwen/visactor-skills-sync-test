"""Editorial type policy; the HTML loads Noto Serif SC through Feishu's CDN."""

FAMILY = '"Noto Serif SC", "Songti SC", "STSong", serif'


def apply_typography(schema):
    schema["appearance"]["typography"]["fontFamily"] = FAMILY

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {
                    "textStyle",
                    "titleStyle",
                    "subTitleStyle",
                    "contentStyle",
                    "markerStyle",
                } and isinstance(child, dict):
                    child["fontFamily"] = FAMILY
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema["body"])
    return schema
